<div align="center">

# ☪️ Al-Ilm — Islamic RAG System

### *بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ*

**An AI-powered Retrieval-Augmented Generation system that delivers authentic, source-backed Islamic answers from the Quran, Hadith, and trusted scholarly resources.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-Latest-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=for-the-badge)](https://trychroma.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [Usage](#-usage) · [Deployment](#-deployment) · [Project Structure](#-project-structure)

---

</div>

## 🌟 Overview

**Al-Ilm** bridges classical Islamic scholarship with modern AI. It intelligently retrieves and synthesizes information from:

- 📖 **The Holy Quran** — All 6,236 ayahs with English translation
- 📚 **Hadith Collections** — Sahih Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasai, Ibn Majah
- 🕌 **Tafsir** — Verse-by-verse commentary from trusted scholars

All answers are **source-attributed** with direct citations — no hallucinations, no unsourced claims.

> **Fallback Mode**: The system works immediately with curated Islamic knowledge, even without the full RAG pipeline. Enable the complete RAG pipeline by running Ollama locally and indexing the Islamic texts.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌐 **Multilingual** | Ask in **Arabic**, **Urdu**, or **English** |
| 📌 **Source-Backed Answers** | Every answer cites exact Quran verse or Hadith reference |
| 🌙 **Dark/Light Mode** | Elegant Islamic-themed design with theme toggle |
| 🔍 **Semantic Search** | ChromaDB vector store for high-accuracy retrieval |
| ⚡ **REST + WebSocket** | Both REST and streaming WebSocket endpoints |
| 📱 **Responsive UI** | Works beautifully on desktop and mobile |
| 📄 **Document Upload** | Upload your own PDF/TXT Islamic texts for indexing |
| 🧠 **RAG Pipeline** | LangGraph-powered intelligent query routing and retrieval |

---

## 🏗️ Architecture

```
User Query (AR / UR / EN)
        │
        ▼
┌───────────────────┐
│   FastAPI Server  │  ◄── REST + WebSocket Endpoints
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│  Quran  │ │    Hadith    │  ◄── Source Retrievers (ChromaDB)
│  Index  │ │    Index     │
└────┬───┘ └──────┬───────┘
     └─────┬──────┘
           ▼
   ┌───────────────┐
   │  LLM (Ollama/ │  ◄── Answer Generation
   │   OpenAI)     │
   └───────┬───────┘
           │
           ▼
   Cited, Source-Backed Answer
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Either **Ollama** (for local LLM) or **OpenAI API key** (for cloud LLM)

### Option 1: Run with Fallback (Immediate — No RAG)

```bash
# 1. Clone and enter the project
git clone https://github.com/hassanimtiaz158/Islamic-RAG-System.git
cd Islamic-RAG-System

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Open http://localhost:8000** in your browser. The app works immediately with curated Islamic knowledge answers and citations.

### Option 2: Full RAG Pipeline (with Ollama)

```bash
# 1. Install Ollama from https://ollama.com
# 2. Pull the model
ollama pull phi3

# 3. Copy environment config
cp .env.example .env

# 4. Start the server (RAG automatically enabled)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 5. (Optional) Index Quran and Hadith data
python scripts/index_all.py
```

### Option 3: OpenAI (Cloud)

```bash
cp .env.example .env
# Edit .env:
#   LLM_PROVIDER=openai
#   LLM_MODEL=gpt-4o-mini
#   OPENAI_API_KEY=sk-...

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 💬 Usage

### Web Interface

Open **http://localhost:8000** after starting the server. Ask questions about:

- "What does Islam say about patience?"
- "ما حكم الصلاة في الإسلام؟"
- "What is the importance of honoring parents?"
- Tell me about Zakat"

### API Example

```python
import requests

response = requests.post("http://localhost:8000/api/ask", json={
    "question": "What does Islam say about patience?",
    "language": "en",
    "sources": ["quran", "hadith_bukhari"]
})

print(response.json())
# {
#   "answer": "Patience (Sabr) is one of the greatest virtues...",
#   "citations": ["[Quran Al-Baqarah 2:153]", "[Bukhari, Zakat, No. 1469]"],
#   "citation_cards": [...],
#   "citation_valid": true,
#   "sources_used": ["quran", "hadith_bukhari"]
# }
```

### Health Check

```bash
curl http://localhost:8000/api/health
# {"status": "ok", "rag_available": true, "llm_provider": "ollama", ...}
```

---

## 🚢 Deployment

### Frontend → Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)

1. Connect your GitHub repository to Vercel
2. Set **Root Directory** to `frontend/`
3. Set **Build Command** to empty
4. Set **Output Directory** to `.`
5. Add env variable: `NEXT_PUBLIC_API_BASE` = your Render backend URL

Or use `vercel.json` included in the project root.

### Backend → Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

1. Push code to GitHub
2. Create a new **Web Service** on Render
3. Connect your repository
4. Use the included `render.yaml` or set manually:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `LLM_PROVIDER` = `openai`
   - `OPENAI_API_KEY` = your OpenAI key
   - `LLM_MODEL` = `gpt-4o-mini`

### Docker

```bash
docker build -t islamic-rag .
docker run -p 8000:8000 islamic-rag
```

---

## 📁 Project Structure

```
Islamic-RAG-System/
│
├── 📂 frontend/             # Web interface (HTML + CSS + JS)
│   ├── index.html           # Main SPA with chat UI
│   ├── css/style.css        # Styling with dark mode support
│   └── js/
│       ├── app.js           # Main app logic, WebSocket, REST
│       └── citations.js     # Citation extraction and rendering
│
├── 📂 src/                  # Core application source
│   ├── api/main.py          # FastAPI server with REST + WebSocket
│   ├── agents/
│   │   ├── islamic_graph.py # LangGraph RAG pipeline
│   │   ├── classifier.py    # Query classification node
│   │   └── state.py         # Graph state definitions
│   ├── core/
│   │   ├── islamic_vectorDB.py  # ChromaDB vector store
│   │   └── islamic_chunker.py   # Document text splitting
│   └── utils/
│       └── citation_engine.py   # Citation extraction & formatting
│
├── 📂 scripts/              # Data ingestion scripts
│   ├── index_all.py         # Full indexing pipeline
│   ├── load_quran.py        # Load Quran from AlQuran.cloud API
│   ├── load_hadiths.py      # Load hadith from HadithAPI.com
│   └── load_tafsir.py       # Load Tafsir from JSON
│
├── 📄 .env.example          # Environment variable template
├── 📄 requirements.txt      # Python dependencies
├── 📄 dockerfile            # Docker configuration
├── 📄 render.yaml           # Render deployment config
├── 📄 vercel.json           # Vercel deployment config
└── 📄 README.md
```

---

## 🛡️ Islamic Safety & Accuracy

The system is designed with several guardrails:

- **Source-Backed Only**: Responses are grounded only in retrieved Islamic sources
- **No Fabrication**: If a source isn't found, the system says: *"I could not find this in the available Islamic sources"*
- **Citation Verification**: Each response is checked for proper citations
- **Respectful Tone**: Maintains a respectful, scholarly tone without overstepping into fatwas
- **Sensitive Topics**: Advises consulting qualified scholars for complex religious rulings

---

## 🤝 Contributing

Contributions are warmly welcomed!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **MIT License**.

---

<div align="center">

**جَزَاكَ اللَّهُ خَيْرًا** — May Allah reward you with goodness.

⭐ Star this repo if you find it useful!

</div>
