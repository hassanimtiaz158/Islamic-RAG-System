# 🕌 Al-Ilm — Islamic Knowledge RAG System

**Al-Ilm** (Arabic: "The Knowledge") is a production-grade Retrieval-Augmented Generation (RAG) system that answers questions about Islam using the Quran, six authentic Hadith collections, and Tafsir Ibn Kathir. Every answer is source-attributed with formatted citations and confidence scores.

## ✨ Key Features

- **Zero-Hallucination Architecture**: Answers ONLY from retrieved sources — never from model knowledge
- **Multi-Step Verification**: Retrieve → Generate → Verify → Enforce Citations → Finalize
- **Confidence Scoring**: Every answer includes a confidence score (0-100%)
- **Islamic Safety Layer**: Prevents fabrication of Quran/Hadith references, adds scholarly disclaimers for sensitive topics
- **Source Type Distinguishes**: Clearly labels Quran, Hadith, Tafsir, and Scholarly Opinion
- **Hybrid Retrieval**: MMR-based vector search with relevance threshold filtering
- **Real-time Streaming**: WebSocket streaming with token-by-token response
- **Triple Fallback**: WebSocket → REST → Built-in demo answers
- **Modern UI**: ChatGPT-like interface with citation sidebar, dark mode, confidence bars

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│   Classifier     │  LLM classifies query → routes to relevant collections
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Retriever      │  MMR search across ChromaDB collections (k=5, threshold=0.3)
│   + Confidence   │  Computes retrieval confidence score
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Synthesis      │  LLM generates answer with strict citation prompt
│   + Pre-check    │  Immediate grounding verification
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Verification   │  Full grounding check + Islamic safety check
│   + Safety       │  Flags unsupported claims, sensitive topics
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Citation       │  Enforces citations, regenerates if missing
│   Enforcement    │  (max 2 retries)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Finalization   │  Adds scholarly disclaimers, overrides if unverified
└────────┬────────┘
         │
         ▼
   Verified Answer + Citations + Confidence Score + Source Types + Safety Flags
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Ollama (local) OR OpenAI API key OR Groq API key

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/islamic-rag-system.git
cd islamic-rag-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your LLM provider settings
```

### Index Data Sources

```bash
# Index all collections (Quran + 6 Hadith books + Tafsir)
python scripts/index_all.py
```

### Run the Server

```bash
# Development
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### Docker

```bash
docker build -t islamic-rag .
docker run -p 8000:8000 -v ./data:/app/data islamic-rag
```

## 📊 Evaluation

```bash
python scripts/evaluate_rag.py
```

Measures: Faithfulness, Context Precision/Recall, Citation Correctness, Hallucination Rate

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama`, `openai`, or `groq` |
| `LLM_MODEL` | `phi3` | Model name for the selected provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `GROQ_API_KEY` | — | Groq API key |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

## 🛡️ Hallucination Prevention

1. **Retrieval-First**: Never answers without retrieved context
2. **Strict Prompts**: LLM instructed to ONLY use provided sources
3. **Citation Enforcement**: Every factual claim must have a citation
4. **Grounding Verification**: Post-generation check that citations exist in context
5. **Islamic Safety Layer**: Detects fabricated references, adds scholar disclaimers
6. **Confidence Scoring**: Low-confidence answers flagged or overridden
7. **Insufficient Evidence Handling**: Admits when sources are lacking

## 📝 API Example

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What does Islam say about patience?", "sources": ["quran", "hadith_bukhari"]}'
```

```json
{
  "answer": "Patience (Sabr) is one of the greatest virtues in Islam...",
  "citations": ["[Quran Al-Baqarah 2:153]", "[Bukhari 1469]"],
  "citation_cards": [...],
  "citation_valid": true,
  "sources_used": ["quran", "hadith_bukhari"],
  "confidence_score": 0.85,
  "verification_passed": true,
  "source_types": ["quran", "hadith"],
  "safety_flags": [],
  "retrieval_confidence": 0.72,
  "insufficient_evidence": false
}
```

---

**بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ**
*In the name of Allah, the Most Gracious, the Most Merciful.*
