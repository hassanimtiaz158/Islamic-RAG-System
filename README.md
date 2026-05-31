<div align="center">

# ☪️ Islamic RAG System

### *بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ*

**An AI-powered Retrieval-Augmented Generation system that delivers authentic, source-backed Islamic answers from the Quran, Hadith, and trusted scholarly resources.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-Latest-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=for-the-badge)](https://trychroma.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[Features](#-features) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Getting Started](#-getting-started) · [Usage](#-usage) · [Project Structure](#-project-structure)

---

</div>

## 🌟 Overview

The **Islamic RAG System** bridges classical Islamic scholarship with modern AI. It intelligently retrieves and synthesizes information from:

- 📖 **The Holy Quran** — Ayahs with contextual tafsir
- 📚 **Hadith Collections** — Bukhari, Muslim, Abu Dawud, Tirmidhi & more
- 🕌 **Scholarly Resources** — Trusted fiqh and Islamic academic texts

All answers are **source-attributed**, grounding every response in authentic Islamic texts — no hallucinations, no unsourced claims.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌐 **Multilingual** | Ask questions in **Arabic**, **Urdu**, or **English** |
| 📌 **Source-Backed Answers** | Every answer cites the exact Quran verse or Hadith reference |
| 🤖 **Agentic Reasoning** | LangGraph-powered intelligent query routing and multi-step reasoning |
| 🔍 **Semantic Search** | ChromaDB vector store for high-accuracy retrieval |
| ⚡ **REST API** | Clean FastAPI endpoints for easy integration |
| 🧠 **Context-Aware** | Understands follow-up questions within a conversation |

---

## 🏗️ Architecture

```
User Query (AR / UR / EN)
        │
        ▼
┌───────────────────┐
│   FastAPI Server  │  ◄── REST Endpoints
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   LangGraph Agent │  ◄── Query Classification & Routing
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│  Quran │ │    Hadith    │  ◄── Source Retrievers
│  Index │ │    Index     │
└────┬───┘ └──────┬───────┘
     └─────┬──────┘
           ▼
   ┌───────────────┐
   │   ChromaDB    │  ◄── Vector Store (Embeddings)
   └───────┬───────┘
           │
           ▼
   ┌───────────────┐
   │  LLM (OpenAI/ │  ◄── Answer Generation
   │  Gemini/etc.) │
   └───────┬───────┘
           │
           ▼
   Cited, Source-Backed Answer
```

> 📐 See the full architecture diagram: [`islamic-RAG architecture.png`](./islamic-RAG%20arctitecture.png)

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com) |
| **AI Orchestration** | [LangChain](https://langchain.com) + [LangGraph](https://langchain-ai.github.io/langgraph/) |
| **Vector Database** | [ChromaDB](https://trychroma.com) |
| **Language** | Python 3.10+ |
| **Frontend** | Custom Web UI (in `/frontend`) |
| **Embeddings** | OpenAI / HuggingFace Sentence Transformers |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- An LLM API key (OpenAI, Google Gemini, etc.) — see [`keysTouse.txt`](./keysTouse.txt)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/hassanimtiaz158/Islamic-RAG-System.git
cd Islamic-RAG-System

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API keys
cp keysTouse.txt .env
# Edit .env and fill in your API keys
```

### Running the Application

```bash
# Start the FastAPI backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser at `http://localhost:8000/docs` to explore the interactive API.

---

## 💬 Usage

### API Example

```python
import requests

response = requests.post("http://localhost:8000/ask", json={
    "question": "What does Islam say about patience?",
    "language": "en"
})

print(response.json())
# {
#   "answer": "...",
#   "sources": [
#     { "type": "Quran", "reference": "Surah Al-Baqarah 2:153" },
#     { "type": "Hadith", "reference": "Sahih Bukhari, Book 70, Hadith 547" }
#   ]
# }
```

### Multilingual Queries

```python
# Arabic
{ "question": "ما حكم الصلاة في الإسلام؟", "language": "ar" }

# Urdu
{ "question": "نماز کی اہمیت کیا ہے؟", "language": "ur" }

# English
{ "question": "What is the importance of prayer in Islam?", "language": "en" }
```

---

## 📁 Project Structure

```
Islamic-RAG-System/
│
├── 📂 src/                     # Core application source code
│   ├── agents/                 # LangGraph agent definitions
│   ├── retrievers/             # Quran & Hadith retrieval logic
│   ├── chains/                 # LangChain pipelines
│   ├── embeddings/             # Embedding model configurations
│   └── main.py                 # FastAPI app entrypoint
│
├── 📂 frontend/                # Web interface
│
├── 📂 scripts/                 # Data ingestion & indexing scripts
│
├── 📂 tests/                   # Test suite
│
├── 📄 requirements.txt         # Python dependencies
├── 📄 keysTouse.txt            # API key reference template
├── 🖼️ islamic-RAG architecture.png  # System architecture diagram
└── 📄 README.md
```

---

## 🤝 Contributing

Contributions are warmly welcomed! Whether it's expanding the Islamic knowledge corpus, improving retrieval accuracy, or supporting more languages — your help matters.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/add-tafsir-source`)
3. Commit your changes (`git commit -m 'Add tafsir source integration'`)
4. Push to the branch (`git push origin feature/add-tafsir-source`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- The Islamic scholarly community whose works form the knowledge foundation of this system
- [LangChain](https://langchain.com) and [LangGraph](https://langchain-ai.github.io/langgraph/) for the AI orchestration framework
- [ChromaDB](https://trychroma.com) for the vector storage layer
- [FastAPI](https://fastapi.tiangolo.com) for the clean, fast API layer

---

<div align="center">

**جَزَاكَ اللَّهُ خَيْرًا** — May Allah reward you with goodness.


⭐ Star this repo if you find it useful!

</div>
