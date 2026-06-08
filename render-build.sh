#!/usr/bin/env bash
# render-build.sh
# Build script for Render deployment
# Handles heavy dependencies gracefully on Render's free tier

set -e

echo "=== Installing Python dependencies ==="
pip install --no-cache-dir -r requirements.txt

echo "=== Build complete ==="
