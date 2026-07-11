#!/usr/bin/env bash
# render-build.sh
# Pre-build script for local development (NOT used by Render deployment).
# Render builds directly from Dockerfile which downloads the model in the builder stage.
# Run this locally to pre-download the embedding model for faster Docker builds.

set -e

echo "=== Pre-downloading embedding model ==="
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

echo "=== Embedding model ready ==="
echo "=== You can now run: docker build -t islamic-rag . ==="
