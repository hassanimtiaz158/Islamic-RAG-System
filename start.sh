#!/bin/bash
# Render start script: serves the API immediately and indexes the vector
# store in the background only when it is empty. Idempotent across restarts
# via a .indexed marker file. Designed for Render free tier (no Shell access).
set -e

STORE_PATH="${VECTOR_STORE_PATH:-data/vectorstore}"
MARKER="$STORE_PATH/.indexed"

# Start the API in the background so the service binds the port and passes
# the health check quickly. It serves demo answers until indexing finishes.
uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
UVICORN_PID=$!

# Forward termination signals to uvicorn for a clean shutdown
trap 'kill -TERM "$UVICORN_PID" 2>/dev/null; wait "$UVICORN_PID"' TERM INT

if [ ! -f "$MARKER" ]; then
  echo "[INDEX] Vector store empty (or wiped) — running index_all.py ..."
  python scripts/index_all.py || echo "[INDEX] index_all.py exited non-zero; will retry next start"

  python - <<PY
import os, chromadb
p = os.environ.get("VECTOR_STORE_PATH", "/app/data/vectorstore")
try:
    c = chromadb.PersistentClient(path=p)
    total = sum(col.count() for col in c.list_collections())
    if total > 0:
        open(os.path.join(p, ".indexed"), "w").close()
        print(f"[INDEX] Done — {total} docs indexed. Marker written.")
    else:
        print("[INDEX] No docs were indexed; will retry on next start.")
except Exception as e:
    print(f"[INDEX] Marker check failed: {e}")
PY
else
  echo "[INDEX] Marker present — skipping indexing."
fi

wait "$UVICORN_PID"
