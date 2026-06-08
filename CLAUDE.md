# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Al-Ilm** (Arabic for "The Knowledge") is an Islamic RAG (Retrieval-Augmented Generation) system that answers questions about Islam using the Quran, six authentic Hadith collections, and Tafsir Ibn Kathir. Every answer is source-attributed with formatted citations.

## Common Commands

### Development
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Run the backend server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Index all data sources (Quran + 6 hadith books)
python scripts/index_all.py
```

### Running Tests
Tests are standalone scripts (no pytest). Run individually:
```bash
python src/agents/test_classifier.py        # Classifier node (MockLLM)
python src/agents/test_islamic_graph.py     # Full LangGraph pipeline (MockLLM)
python src/agents/final_test_query.py       # Full pipeline with real vector store
python src/core/test_chunker.py             # Quran/Hadith/Tafsir splitters
python src/core/test_vectorDB.py            # Vector store init, indexing, retrieval
python scripts/test_citation_engine.py      # Citation extraction and card formatting
python scripts/test_quran_query.py          # Quran vector search
python scripts/test_tafsir.py               # Tafsir JSON loader
```

### Docker
```bash
docker build -t islamic-rag .
docker run -p 8000:8000 islamic-rag
```

## Architecture

### RAG Pipeline (`src/agents/`)

Three-node LangGraph stateful graph (`islamic_graph.py`):

1. **Classifier** (`classifier.py`) — Uses LLM to determine which ChromaDB collections to search. Falls back to `["quran", "hadith_bukhari"]` if LLM is unavailable.
2. **Unified Retriever** — MMR search across ChromaDB collections (k=4, fetch_k=16, lambda_mult=0.75). Thread-safe via `EMBED_LOCK`.
3. **Synthesis** — Builds context from retrieved docs, generates cited answer using `SYNTHESIS_PROMPT`, extracts citations via regex, formats citation cards.

State is defined in `state.py` using `TypedDict`.

### Vector Store (`src/core/`)

- **ChromaDB** persistent client at `data/vectorstore/`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (CPU, batch_size=64, normalized)
- 10 collections: `quran`, `hadith_bukhari`, `hadith_muslim`, `hadith_dawud`, `hadith_tirmidhi`, `hadith_nasai`, `hadith_ibnmajah`, `tafsir`, `fiqh`, `seerah`
- Manager class in `islamic_vectorDB.py` with thread-safe embedding lock
- Chunkers in `islamic_chunker.py` — specialized splitters for Quran (per-ayah), Hadith (per-hadith), and Tafsir (per-verse)

### Citation Engine (`src/utils/citation_engine.py`)

- Regex-based extraction for Quran (`[Quran SurahName Ch:V]`), 6 hadith collections, and tafsir
- Generates URLs: `quran.com/{surah}/{ayah}` and `sunnah.com/{book}:{number}`
- `enforce_citations()` — LangGraph node that regenerates if no citations found
- `format_citation_cards()` — Formats for frontend sidebar with icons and colors

### API (`src/api/main.py`)

- **FastAPI** server mounting static frontend from `frontend/`
- `POST /api/ask` — Main chat endpoint (query, language, sources)
- `POST /api/index-document` — Upload PDF/TXT for indexing
- `GET /api/verify-citation` — Verify Quran citation via AlQuran.cloud API
- `WS /ws/ask` — WebSocket streaming (token-by-token → `done` with citations)
- `GET /api/health` — Health check

### Frontend (`frontend/`)

- Vanilla JS SPA (no framework, no build step)
- **Triple-redundancy fallback**: WebSocket → REST → built-in demo answers (5 topics via keyword matching)
- `app.js` — Main logic (WebSocket/REST switching, streaming, demo fallback)
- `citations.js` — Citation extraction/rendering, Arabic verse fetching from AlQuran.cloud
- `search-history.js` — Search history sidebar (localStorage)
- Theme support (dark/light) with Islamic green/gold color scheme
- Configurable API base via `window.__API_BASE__`

### Data

- 851MB across 291 files tracked via DVC (local S3-like remote at `S3/`)
- **Quran**: 6,236 ayahs as 114 per-surah CSVs + `holy_quran.json` (loader: AlQuran.cloud API)
- **Hadith**: Bukhari (8 PDF volumes), Muslim (5 PDF volumes), plus mixed formats in `Hadees/` (loader: HadithAPI.com)
- **Tafsir**: `tafsir_ibn_kathir.json`
- **Fiqh**: 80+ PDFs
- **Training data**: Parquet files in `data/training/`

### Configuration (`.env`)

Key variables:
- `LLM_PROVIDER` — `ollama` or `openai`
- `OLLAMA_BASE_URL` — default `http://localhost:11434`
- `LLM_MODEL` — `phi3` (Ollama) or `gpt-4o-mini` (OpenAI)
- `OPENAI_API_KEY` / `GROQ_API_KEY` — API keys as needed
- `HOST` / `PORT` — server binding

## Key Design Patterns

- **Thread-safe ChromaDB access**: Global `EMBED_LOCK` in `islamic_vectorDB.py` since ChromaDB's embedding function is not thread-safe
- **Graceful degradation**: Every component has fallbacks — LLM unavailable → default collections; RAG unavailable → curated fallback answers; backend unreachable → demo mode
- **Citation enforcement**: The synthesis node checks for citations in the output and regenerates if none are found
- **MMR retrieval**: Uses Maximal Marginal Relevance (lambda_mult=0.75) for diverse, non-redundant results

## LLM Integration Notes

The project uses **LangChain** and **LangGraph** (v0.0.20+). The codebase has not been upgraded to newer LangChain versions that restructured imports (e.g., `langchain_community` split, `langgraph` prebuilt agents). If upgrading, expect import changes throughout `src/agents/`, `src/core/`, and `scripts/`.
