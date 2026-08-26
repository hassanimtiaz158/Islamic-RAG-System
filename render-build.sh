#!/usr/bin/env bash
# render-build.sh
# Optional local helper for the Docker build path (NOT used by Render's own
# deployment, which builds natively from requirements.txt — see README.md).
# The Dockerfile already pre-fetches the embedding model in its build stage,
# so running this script by hand is only useful to warm your local pip/model
# cache before `docker build` for a faster first build.

set -e

echo "=== Pre-downloading embedding model (fastembed/ONNX, matches src/core/islamic_vectorDB.py) ==="
python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"

echo "=== Embedding model ready ==="
echo "=== You can now run: docker build -t islamic-rag . ==="
