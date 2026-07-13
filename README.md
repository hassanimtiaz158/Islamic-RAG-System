# ٱلْعِلْم • Al-Ilm

<p align="center">
  <img src="https://img.shields.io/badge/Islam-RAG-1a5c38?style=for-the-badge" alt="Islam RAG" />
  <img src="https://img.shields.io/badge/Zero--Hallucination-verified-bf9b30?style=for-the-badge" alt="Zero Hallucination" />
  <img src="https://img.shields.io/badge/LangGraph-11--step%20pipeline-ff6f00?style=for-the-badge" alt="LangGraph" />
  <img src="https://img.shields.io/badge/FastAPI-%2B%20WebSocket-009688?style=for-the-badge" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Frontend-Vanilla%20JS-323330?style=for-the-badge&logo=javascript&logoColor=F7DF1E" alt="Vanilla JS" />
</p>

<p align="center">
  <i>“And say: My Lord, increase me in knowledge.” — Quran 20:114</i>
</p>

**Al-Ilm** (Arabic for *"The Knowledge"*) is a Retrieval-Augmented Generation system that answers
questions about Islam **strictly from authenticated sources** — the Quran, the six canonical Hadith
collections, Tafsir Ibn Kathir, Fiqh, Seerah, and user-uploaded documents. Every answer is
**source-attributed**, **confidence-scored**, and protected by an **Islamic safety layer** that
prevents fabricating Quran/Hadith references.

> 🛡️ **Zero-Hallucination by design.** The model never answers from its own knowledge — only from
> retrieved, cited passages. If the sources don't support an answer, the system says so.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Zero-Hallucination** | Answers synthesized **only** from retrieved context; citations are cross-checked against the source. |
| **11-Step Verification Pipeline** | Retrieve → Translate → Retrieve → Synthesize → Verify → Fact-Check → Enforce Citations → Finalize → Follow-ups → Translate → Respond. |
| **Confidence Scoring** | Each answer carries a 0–100% confidence derived from retrieval, synthesis, and verification. |
| **Islamic Safety Layer** | Flags sensitive topics, blocks fabricated references, appends scholarly disclaimers. |
| **Rich Citations** | Quran / Hadith / Tafsir / Fiqh clearly distinguished, with live verification badges and source links. |
| **Hybrid Retrieval** | MMR-based vector search (`lambda_mult=0.75`) with relevance-threshold filtering across 10 collections. |
| **Real-time Streaming** | WebSocket token-by-token streaming with REST + built-in demo fallbacks (triple redundancy). |
| **Multilingual** | English, Arabic, and Urdu interface with LLM-based query/response translation. |
| **Verse Triplets** | Quran citations render Arabic / English / Urdu text fetched from AlQuran.cloud. |
| **User Uploads** | Index your own PDF/TXT documents and query them alongside the canonical sources. |

---

## 🏛️ Architecture

### RAG Pipeline (`src/agents/islamic_graph.py`)
An 11-step stateful **LangGraph** workflow:

```
1. Classifier        → selects which ChromaDB collections to search
2. Query Translation → non-English → English for vector search
3. Retriever         → MMR search across collections (k=5, threshold 0.3)
4. Synthesis         → builds cited answer from retrieved context
5. Verification      → grounding + Islamic safety check
6. Fact Check        → cross-references every citation vs. context
7. Citation Enforce  → regenerates if citations missing/invalid (≤2 retries)
8. Finalization      → disclaimers + verse triplets
9. Follow-ups        → suggests 3 related questions
10. Translation      → back to the user's language
11. Response         → streamed to the client
```

### Vector Store (`src/core/islamic_vectorDB.py`)
- **ChromaDB** persistent client, embedding model `sentence-transformers/all-MiniLM-L6-v2` (CPU, normalized).
- **10 collections:** `quran`, `hadith_bukhari`, `hadith_muslim`, `hadith_dawud`,
  `hadith_tirmidhi`, `hadith_nasai`, `hadith_ibnmajah`, `tafsir`, `fiqh`, `seerah`, plus `user_uploaded`.
- Thread-safe embedding via a global `EMBED_LOCK`.

### Citation Engine (`src/utils/citation_engine.py`)
Regex extraction → formatted cards → URL generation (`quran.com`, `sunnah.com`) → grounding
verification → hallucination detection.

### Frontend (`frontend/`)
A dependency-free Vanilla JS SPA with a ChatGPT-like UI, citation sidebar, dark mode, and
confidence bars. Triple-redundancy: **WebSocket → REST → curated demo answers**.

---

## 📁 Project Structure

```
islamic-rag-system/
├── src/
│   ├── api/            # FastAPI app, routers (v1), auth, admin
│   ├── agents/         # LangGraph pipeline (classifier, graph, state)
│   ├── core/           # vector store + chunkers
│   ├── utils/          # citation engine, prompts
│   ├── config/         # pydantic-settings
│   └── services/       # cache, db, llm
├── scripts/            # index_all, load_quran/hadiths/tafsir/fiqh, evaluate
├── frontend/           # Vanilla JS SPA (js/, css/, index.html, admin.html)
├── data/               # quran, hadith, tafsir, fiqh (PDFs), seerah, vectorstore
└── requirements.txt    # Python dependencies
```

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.11+
- *(Optional)* Ollama, or API keys for Groq / OpenAI
- *(Optional)* MongoDB + Redis (app degrades gracefully without them)

```bash
# 1. Clone & enter
git clone <your-repo-url> && cd islamic-rag-system

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env           # then edit LLM_PROVIDER / keys

# 5. Index the knowledge base (Quran + 6 Hadith + Tafsir + Fiqh)
python scripts/index_all.py

# 6. Run the backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** — the chat UI is served directly by the backend.

---

## ⚙️ Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | `ollama` / `openai` / `groq` | `groq` |
| `LLM_MODEL` | model id matching provider | `llama-3.1-8b-instant` |
| `OPENAI_API_KEY` / `GROQ_API_KEY` | API keys as needed | — |
| `OLLAMA_BASE_URL` | Ollama endpoint | `http://localhost:11434` |
| `HADITH_API_KEY` / `QURAN_API_KEY` | required for indexing | — |
| `MONGODB_URL` / `REDIS_URL` | auth & cache (optional) | — |
| `JWT_SECRET` | auth signing secret | — |
| `VECTOR_STORE_PATH` | ChromaDB persistence dir | `data/vectorstore` |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `localhost` only |

---

## 📚 Indexing

```bash
python scripts/index_all.py     # full pipeline: quran, hadith×6, tafsir, fiqh, seerah
```

- `fiqh` is loaded from bundled PDFs in `data/fiqh` (PyMuPDF).
- `seerah` is loaded if `data/seerah` contains PDFs/TXT; otherwise it is skipped cleanly.
- Individual loaders: `load_quran.py`, `load_hadiths.py`, `load_tafsir.py`, `load_fiqh.py`.
- Evaluate quality (faithfulness, citation correctness, hallucination rate):
  ```bash
  python scripts/evaluate_rag.py
  ```

---

## 🔌 API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/ask` | Main chat (query, language, sources) |
| `WS` | `/ws/ask` | Streaming chat (token-by-token → `done` + citations) |
| `POST` | `/api/index-document` | Upload & index a PDF/TXT |
| `GET` | `/api/verify-citation` | Verify a Quran citation via AlQuran.cloud |
| `POST` | `/api/translate-verse` | Translate a verse triplet |

---

## 🌐 Deployment (manual)

This project is deployed manually — no Dockerfile, `render.yaml`, or CI is committed.

### Render (backend + API)
1. Push to GitHub → Render **New + → Web Service** → connect the repo.
2. **Language:** Python 3.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
5. **Health Check Path:** `/api/health`
6. **Environment** → add:
   - `GROQ_API_KEY` (or `OPENAI_API_KEY`)
   - `JWT_SECRET` (random string)
   - `LLM_PROVIDER=groq`, `LLM_MODEL=llama-3.1-8b-instant`
   - `ENVIRONMENT=production`, `PYTHONUNBUFFERED=1`
   - `VECTOR_STORE_PATH=/app/data/vectorstore` (or your disk mount)
   - If serving the frontend separately (Vercel): `ALLOWED_ORIGINS=https://<app>.vercel.app,https://<app>.onrender.com`
7. **Start Command:** `bash start.sh` (starts the API and indexes the store only when empty).
8. **Deploy.** The backend serves the UI from `frontend/` same-origin. On first start it indexes in the background (demo answers until done); later cold starts skip indexing thanks to a `.indexed` marker.
9. *(Recommended)* Attach a **Disk** at `VECTOR_STORE_PATH` so the indexed data and marker persist across restarts. Without a disk, the free plan re-indexes on every cold start.

> The embedding model (~400 MB) downloads on the first request and is then cached.

### Vercel (frontend only, optional)
1. Vercel **Add New → Project** → import the repo.
2. **Framework Preset:** Other · **Root Directory:** `frontend` · **Build Command:** *(none)* · **Output Directory:** `frontend`.
3. Point the API at your Render backend (`frontend/js/app.js` line 8):
   ```js
   const API_BASE = 'https://<your-app>.onrender.com' || '';
   ```
4. Add a `vercel.json` in `frontend/` for SPA deep links:
   ```json
   { "rewrites": [ { "source": "/(.*)", "destination": "/index.html" } ] }
   ```
5. Make sure Render's `ALLOWED_ORIGINS` includes the Vercel URL (step 6 above).

---

## 🧪 Tests

Standalone scripts (no pytest):
```bash
python src/agents/test_classifier.py
python src/agents/test_islamic_graph.py
python src/agents/final_test_query.py
python scripts/test_citation_engine.py
python scripts/test_quran_query.py
```

---

## 🤝 Contributing

Contributions are welcome. Please open an issue or PR. This project prioritizes **source
authenticity and zero hallucination** — any change to the generation pipeline must preserve
citation enforcement and grounding verification.

---

<p align="center">
  <sub>Built for the Ummah • Knowledge with Attribution</sub>
</p>
