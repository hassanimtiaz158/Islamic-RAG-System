# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Al-Ilm** (Arabic for "The Knowledge") is an Islamic RAG (Retrieval-Augmented Generation) system that answers questions about Islam using the Quran, six authentic Hadith collections, and Tafsir Ibn Kathir. Every answer is source-attributed with formatted citations and confidence scores.

## Key Features

- **Zero-Hallucination Architecture**: Answers ONLY from retrieved sources — never from model knowledge
- **Multi-Step Verification**: Retrieve → Generate → Verify → Enforce Citations → Fact Check → Finalize
- **Confidence Scoring**: Every answer includes a confidence score (0-100%) based on retrieval, synthesis, and verification
- **Islamic Safety Layer**: Prevents fabrication of Quran/Hadith references, adds scholarly disclaimers for sensitive topics
- **Source Type Distinguishing**: Clearly labels Quran, Hadith, Tafsir, and Scholarly Opinion in citations
- **Hybrid Retrieval**: MMR-based vector search with relevance threshold filtering (lambda_mult=0.75)
- **Real-time Streaming**: WebSocket streaming with token-by-token response
- **Triple Fallback**: WebSocket → REST → Built-in demo answers (5 topics via keyword matching)
- **Modern UI**: ChatGPT-like interface with citation sidebar, dark mode, confidence bars
- **Multilingual Support**: English, Arabic, and Urdu interfaces with LLM-based translation

## Common Commands

### Development
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Run the backend server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Index all data sources (Quran + 6 hadith books)
python scripts/index_all.py

# Evaluate the RAG system (faithfulness, context precision/recall, citation correctness, hallucination rate)
python scripts/evaluate_rag.py

# Load individual data sources (useful for debugging)
python scripts/load_quran.py
python scripts/load_hadiths.py
python scripts/load_tafsir.py
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

An 11-step LangGraph stateful graph (`islamic_graph.py`):

1. **Classifier** (`classifier.py`) — Uses LLM to determine which ChromaDB collections to search. Falls back to `["quran", "hadith_bukhari"]` if LLM is unavailable. Includes keyword-based routing with English/Arabic/Urdu patterns.
2. **Query Translation** — Translates non-English queries to English for vector search (the vector store contains English content).
3. **Unified Retriever** — MMR search across ChromaDB collections (k=5, score threshold=0.3). Thread-safe via `EMBED_LOCK`. Computes retrieval confidence.
4. **Synthesis** — Builds context from retrieved docs, generates cited answer using `SYNTHESIS_PROMPT`, extracts citations via regex.
5. **Verification** — Checks answer grounding (whether the answer is supported by the retrieved context) and Islamic safety (flags sensitive topics, adds scholarly disclaimers).
6. **Fact Check** — Cross-references every citation in the response against the actual retrieved context to detect hallucinated citations.
7. **Citation Enforcement** (`enforce_citations()`) — Regenerates the answer if no citations found or if citations are invalid (max 2 retries).
8. **Finalization** — Adds scholarly disclaimers for sensitive topics, builds verse triplets for Quran citations (Arabic/English/Urdu display).
9. **Follow-up Suggestions** — Generates 3 relevant follow-up questions based on the Q&A.
10. **Response Translation** — Translates the English response back to the user's selected language (preserves citations and Islamic terminology).
11. **END** — Returns the final state.

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
- `verify_answer_grounding()` — Checks if the answer is grounded in the retrieved context
- `check_islamic_safety()` — Flags unsupported claims and sensitive topics
- `cross_reference_citations()` — Verifies each citation against the retrieved context
- `build_verse_triplets()` — Builds Arabic/English/Urdu display triplets for Quran verses

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
- `LLM_PROVIDER` — `ollama`, `openai`, or `groq`
- `OLLAMA_BASE_URL` — default `http://localhost:11434`
- `LLM_MODEL` — `phi3` (Ollama) or `gpt-4o-mini` (OpenAI) or `llama-3.1-8b-instant` (Groq)
- `OPENAI_API_KEY` / `GROQ_API_KEY` — API keys as needed
- `HOST` / `PORT` — server binding

## Key Design Patterns

- **Thread-safe ChromaDB access**: Global `EMBED_LOCK` in `islamic_vectorDB.py` since ChromaDB's embedding function is not thread-safe
- **Zero-Hallucination Architecture**: Answers ONLY from retrieved sources — never from model knowledge
- **Multi-Step Verification**: Retrieve → Generate → Verify → Enforce Citations → Fact Check → Finalize
- **Confidence Scoring**: Every answer includes a confidence score (0-100%) based on retrieval, synthesis, and verification
- **Islamic Safety Layer**: Prevents fabrication of Quran/Hadith references, adds scholarly disclaimers for sensitive topics
- **Source Type Distinguishing**: Clearly labels Quran, Hadith, Tafsir, and Scholarly Opinion in citations
- **Hybrid Retrieval**: MMR-based vector search with relevance threshold filtering
- **Real-time Streaming**: WebSocket streaming with token-by-token response
- **Graceful Degradation**: Every component has fallbacks — LLM unavailable → default collections; RAG unavailable → curated fallback answers; backend unreachable → demo mode
- **Citation Enforcement**: The synthesis node checks for citations in the output and regenerates if none are found (up to 2 retries)
- **MMR Retrieval**: Uses Maximal Marginal Relevance (lambda_mult=0.75) for diverse, non-redundant results
- **Verse Triplets**: For Quran citations, fetches Arabic/English/Urdu text for rich display in frontend

## LLM Integration Notes

The project uses **LangChain** and **LangGraph** (v0.0.20+). The codebase has not been upgraded to newer LangChain versions that restructured imports (e.g., `langchain_community` split, `langgraph` prebuilt agents). If upgrading, expect import changes throughout `src/agents/`, `src/core/`, and `scripts/`.