# ═══════════════════════════════════════════════════════════════
# Al-Ilm Islamic RAG System — Multi-stage Production Dockerfile
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Builder (installs compiled deps + embedding model) ──
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build-time system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (maximizes layer cache)
COPY requirements.txt .

# Install Python deps into a virtual env (clean copy later)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model (~400MB) — set HF_HOME inside venv so the
# model files are carried over when we COPY --from=builder in stage 2
ENV HF_HOME=/opt/venv/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"


# ── Stage 2: Runtime (minimal, non-root) ──
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    VECTOR_STORE_PATH=/app/data/vectorstore

WORKDIR /app

# Install only runtime system deps (no build-essential, no gcc, no git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appgroup \
    && useradd --system --gid appgroup --home-dir /app --shell /bin/bash appuser

# Copy virtual env from builder (includes pip packages + downloaded model)
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY src/ ./src/
COPY _run_index.py .
COPY requirements.txt .

# Create data directories and set ownership
RUN mkdir -p /app/data/vectorstore /app/data/training /app/data/tafsir \
         /app/data/quran /app/data/hadith /app/data/fiqh /app/data/seerah \
    && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
# Single worker: in-memory caches and RAG graph are per-process.
# Use gunicorn with multiple workers only if you move caching to Redis.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
