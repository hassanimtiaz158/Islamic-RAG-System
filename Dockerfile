# Al-Ilm Islamic RAG System — production image
FROM python:3.11-slim

WORKDIR /app

# System deps needed by chromadb / pymupdf at build+runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-fetch the FastEmbed ONNX embedding model used by src/core/islamic_vectorDB.py
# so the first request after a cold start isn't slow.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    VECTOR_STORE_PATH=/app/data/vectorstore

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

RUN chmod +x start.sh
CMD ["./start.sh"]
