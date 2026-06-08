# src/api/main.py
"""
Islamic Knowledge RAG API — FastAPI application
Provides chat/query, document upload, citation verification, and health check.
"""

import os
import threading
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("islamic-rag")

# ── Environment ──
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "phi3")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── RAG dependencies (lazy init to keep server startup fast) ──
vector_store = None
graph = None
_rag_initialized = False
_rag_init_lock = threading.Lock()


def _init_rag():
    """Lazy initialization of the RAG pipeline. Called on first request."""
    global vector_store, graph, _rag_initialized
    with _rag_init_lock:
        if _rag_initialized:
            return
        _rag_initialized = True  # Mark as initialized BEFORE attempting import to prevent re-entry
    try:
        from src.core.islamic_vectorDB import IslamicVectorStore
        from src.agents.islamic_graph import build_islamic_graph

        vector_store = IslamicVectorStore()
        graph = build_islamic_graph(vector_store)
        logger.info("RAG pipeline initialized successfully")
    except Exception as e:
        logger.warning(f"RAG pipeline not available: {e}")
        logger.warning("Using fallback demo mode.")


# =========================
# APP SETUP
# =========================
app = FastAPI(
    title="Al-Ilm — Islamic Knowledge RAG API",
    version="1.1.0",
    description="AI-powered Islamic knowledge chatbot with source-backed answers from Quran, Hadith, and Tafsir.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend path (mounted after API routes)
FRONTEND_PATH = Path(__file__).resolve().parent.parent.parent / "frontend"


# =========================
# REQUEST/ RESPONSE MODELS
# =========================
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User's question about Islam")
    language: str = Field(default="en", pattern="^(en|ar|ur)$")
    sources: list[str] = Field(default_factory=lambda: ["quran", "hadith_bukhari"])


class QueryResponse(BaseModel):
    answer: str
    citations: list[str] = []
    citation_cards: list[dict] = []
    citation_valid: bool = False
    sources_used: list[str] = []


# =========================
# FALLBACK KNOWLEDGE BASE
# =========================
FALLBACK_ANSWERS = {
    "patience": {
        "answer": 'Patience (Sabr) is one of the greatest virtues in Islam. Allah says: "O you who have believed, seek help through patience and prayer. Indeed, Allah is with the patient." [Quran Al-Baqarah 2:153]\n\n"And We will surely test you with something of fear and hunger and a loss of wealth and lives and fruits, but give good tidings to the patient." [Quran Al-Baqarah 2:155]\n\nThe Prophet ﷺ said: "No one has been given anything better than patience." [Bukhari 1469]\n\nHe also said: "How wonderful is the affair of the believer! All his affairs are good. If something good happens to him he is grateful, and if something bad happens to him, he is patient." [Muslim 2999]',
        "citations": ["[Quran Al-Baqarah 2:153]", "[Quran Al-Baqarah 2:155]", "[Bukhari 1469]", "[Muslim 2999]"],
    },
    "parent": {
        "answer": 'Islam places the highest importance on honoring parents. Allah commands: "And your Lord has decreed that you worship none but Him, and that you be dutiful to your parents." [Quran Al-Isra 17:23]\n\n"And lower to them the wing of humility out of mercy and say: My Lord, have mercy upon them as they brought me up when I was small." [Quran Al-Isra 17:24]\n\nThe Prophet ﷺ was asked: "Which deed is the best?" He replied: "Prayer at its proper time." He was asked: "Then what?" He said: "Kindness to parents." [Bukhari 527]\n\nHe also said: "Paradise lies at the feet of mothers." [Ibn Majah 2781]',
        "citations": ["[Quran Al-Isra 17:23]", "[Quran Al-Isra 17:24]", "[Bukhari 527]", "[Ibn Majah 2781]"],
    },
    "zakat": {
        "answer": 'Zakat is the third pillar of Islam, an obligatory charity upon every eligible Muslim. Allah commands: "And establish prayer and give zakat." [Quran Al-Baqarah 2:110]\n\nZakat is 2.5% of wealth held above nisab for one lunar year. The nisab for gold is 85 grams and for silver is 595 grams.\n\nThe Prophet ﷺ said: "Islam is built upon five pillars: testifying there is no god but Allah and Muhammad is His Messenger, establishing prayer, giving zakat, performing Hajj, and fasting Ramadan." [Bukhari 8]\n\nAllah specifies eight categories: "Zakah expenditures are only for the poor and for the needy and for those employed to collect it and for bringing hearts together and for freeing captives and for those in debt and for the cause of Allah and for the traveler." [Quran At-Tawbah 9:60]',
        "citations": ["[Quran Al-Baqarah 2:110]", "[Bukhari 8]", "[Quran At-Tawbah 9:60]"],
    },
    "fasting": {
        "answer": 'Fasting (Sawm) is the fourth pillar of Islam. Allah commands: "O you who have believed, decreed upon you is fasting as it was decreed upon those before you that you may become righteous." [Quran Al-Baqarah 2:183]\n\n"The month of Ramadan in which was revealed the Quran, a guidance for mankind and clear proofs of guidance and criterion." [Quran Al-Baqarah 2:185]\n\nThe Prophet ﷺ said: "Whoever fasts Ramadan with faith and seeking reward, his previous sins will be forgiven." [Bukhari 38]\n\nHe also said: "When Ramadan comes, the gates of Paradise are opened, the gates of Hell are closed, and the devils are chained." [Bukhari 1899]',
        "citations": ["[Quran Al-Baqarah 2:183]", "[Quran Al-Baqarah 2:185]", "[Bukhari 38]", "[Bukhari 1899]"],
    },
    "prayer": {
        "answer": 'Salah (prayer) is the second pillar of Islam and the most important act of worship after faith. Allah says: "Indeed, prayer prohibits immorality and wrongdoing, and the remembrance of Allah is greater." [Quran Al-Ankabut 29:45]\n\n"And establish prayer and give zakat, and whatever good you put forward for yourselves, you will find it with Allah." [Quran Al-Baqarah 2:110]\n\nThe Prophet ﷺ said: "The first thing the servant will be asked about on the Day of Judgment is his prayer. If it is sound, the rest of his deeds will be sound." He also said: "The key to Paradise is prayer."\n\nThe five daily prayers are Fajr (2 rakats), Dhuhr (4), Asr (4), Maghrib (3), and Isha (4).',
        "citations": ["[Quran Al-Ankabut 29:45]", "[Quran Al-Baqarah 2:110]"],
    },
    "music": {
        "answer": 'The majority of Islamic scholars hold that musical instruments (except the duff/hand drum at weddings) are prohibited. Allah says: "And of the people is he who buys the amusement of speech to mislead from the way of Allah without knowledge and who takes it in ridicule." [Quran Luqman 31:6]\n\nThe Prophet ﷺ said: "There will be among my nation people who will make permissible fornication, silk, alcohol, and musical instruments." [Bukhari 5590]\n\nHowever, the duff (hand drum) is permitted at weddings and Eid celebrations. [Tirmidhi 1089]',
        "citations": ["[Quran Luqman 31:6]", "[Bukhari 5590]", "[Tirmidhi 1089]"],
    },
    "honesty": {
        "answer": 'Truthfulness is one of the most emphasized virtues in Islam. Allah commands: "O you who have believed, fear Allah and be with the truthful." [Quran At-Tawbah 9:119]\n\nThe Prophet ﷺ said: "Adhere to truthfulness, for truthfulness leads to righteousness, and righteousness leads to Paradise. A man continues to tell the truth until he is recorded with Allah as a truthful person." [Bukhari 6094]\n\nHe also said: "Truth leads to piety and piety leads to Paradise. A man persists in speaking the truth until he is enrolled with Allah as a truthful person. Lying leads to obscenity and obscenity leads to Hell. A man keeps lying until he is enrolled with Allah as a liar." [Muslim 2607]',
        "citations": ["[Quran At-Tawbah 9:119]", "[Bukhari 6094]", "[Muslim 2607]"],
    },
    "kindness": {
        "answer": 'Kindness (Rahma) is central to the teachings of Islam. Allah says: "And We have not sent you, [O Muhammad], except as a mercy to the worlds." [Quran Al-Anbiya 21:107]\n\nThe Prophet ﷺ said: "Allah is kind and loves kindness, and He grants reward for kindness that He does not grant for harshness." [Muslim 2593]\n\nHe also said: "Whoever is not merciful to others, will not be treated mercifully." [Bukhari 5997]\n\nRegarding animals, the Prophet said: "A man saw a dog eating mud from thirst, so he filled his shoe with water and gave it to the dog. So Allah appreciated his deed and forgave him." [Bukhari 2466]',
        "citations": ["[Quran Al-Anbiya 21:107]", "[Muslim 2593]", "[Bukhari 5997]", "[Bukhari 2466]"],
    },
    "charity": {
        "answer": 'Charity (Sadaqah) is deeply encouraged in Islam beyond the obligatory Zakat. Allah says: "The example of those who spend their wealth in the way of Allah is like a seed of grain which grows seven spikes; in each spike is a hundred grains." [Quran Al-Baqarah 2:261]\n\nThe Prophet ﷺ said: "Charity does not decrease wealth." [Muslim 2588]\n\nHe also said: "Every act of goodness is charity. Smiling at your brother is charity. A good word is charity. Every step you take toward prayer is charity. Removing a harmful object from the road is charity." [Muslim 1009]\n\n"He who sleeps with a full stomach while his neighbor goes hungry is not one of us."',
        "citations": ["[Quran Al-Baqarah 2:261]", "[Muslim 2588]", "[Muslim 1009]"],
    },
}

FALLBACK_CITATION_CARDS = [
    {
        "raw": "[Quran Al-Baqarah 2:153]",
        "source": "QURAN",
        "reference": "Surah Al-Baqarah, Verse 153",
        "url": "https://quran.com/2/153",
        "verified": True,
        "icon": "book-open",
        "color": "#1A6B2E",
    },
    {
        "raw": "[Bukhari 1469]",
        "source": "HADITH",
        "reference": "Sahih Bukhari, Hadith 1469",
        "url": "https://sunnah.com/bukhari:1469",
        "verified": True,
        "icon": "scroll",
        "color": "#C9A84C",
    },
]


def _get_fallback_answer(query: str) -> QueryResponse:
    """Generate a response from the curated fallback knowledge base."""
    q = query.lower()

    # Score each entry by number of keyword matches for best match
    scored = []
    for key, entry in FALLBACK_ANSWERS.items():
        words = key.split()
        score = sum(1 for word in words if word in q)
        scored.append((score, key, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_key, best_entry = scored[0]

    if best_score > 0:
        return QueryResponse(
            answer=best_entry["answer"],
            citations=best_entry["citations"],
            citation_cards=FALLBACK_CITATION_CARDS,
            citation_valid=True,
            sources_used=["quran", "hadith_bukhari"],
        )

    return QueryResponse(
        answer=(
            f'Bismillah. Thank you for your question about "{query}".\n\n'
            "The RAG pipeline is currently unavailable, but I can still help with common Islamic topics. "
            "Try asking about:\n"
            "• Patience (Sabr) and trials\n"
            "• Honoring parents\n"
            "• Zakat and charity\n"
            "• Fasting and Ramadan\n"
            "• Prayer (Salah)\n"
            "• Honesty and truthfulness\n"
            "• Kindness to animals and people\n\n"
            "Note: For full AI-powered answers with Quran and Hadith sources, "
            "connect the backend to an LLM (OpenAI, Groq, or Ollama)."
        ),
        citations=[],
        citation_cards=[],
        citation_valid=False,
        sources_used=[],
    )


# =========================
# REST API ENDPOINTS
# =========================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "rag_available": graph is not None,
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "version": "1.1.0",
    }


@app.post("/api/ask", response_model=QueryResponse)
async def ask_islamic(req: QueryRequest):
    """
    Main chat endpoint.
    Uses the RAG pipeline if available, otherwise falls back to curated knowledge.
    """
    _init_rag()
    if graph is not None:
        try:
            result = graph.invoke({
                "query": req.query,
                "language": req.language,
                "retrieved_docs": {},
                "routing": [],
                "iteration": 0,
            })

            answer = result.get("response", "")
            citations = result.get("citations", [])
            citation_cards = result.get("citation_cards", [])
            citation_valid = result.get("citation_valid", False)
            sources_used = list(result.get("retrieved_docs", {}).keys())

            return QueryResponse(
                answer=answer,
                citations=citations,
                citation_cards=citation_cards,
                citation_valid=citation_valid,
                sources_used=sources_used,
            )
        except Exception as e:
            logger.error(f"RAG pipeline error: {e}")
            # Fall through to fallback

    return _get_fallback_answer(req.query)


@app.post("/api/index-document")
async def index_document(file: UploadFile = File(...)):
    """
    Upload and index an Islamic text document (PDF or TXT).
    The document is split into chunks and indexed into the vector store.
    """
    _init_rag()
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail="Vector store is not available. Please configure the RAG pipeline first.",
        )

    try:
        content = await file.read()

        # Try to extract text depending on file type
        text = None
        if file.filename and file.filename.lower().endswith(".pdf"):
            try:
                import fitz  # PyMuPDF
                with fitz.open(stream=content, filetype="pdf") as doc:
                    text = "\n\n".join(page.get_text() for page in doc)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to extract text from PDF: {e}. Try uploading a .txt file.",
                )
        else:
            # TXT or other text files
            text = content.decode("utf-8", errors="replace")

        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="No text content found in the uploaded file.")

        from langchain_core.documents import Document

        # Simple chunking by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        docs = [
            Document(
                page_content=p,
                metadata={
                    "source": "user_upload",
                    "filename": file.filename,
                    "citation": f"[Uploaded: {file.filename}]",
                },
            )
            for p in paragraphs
        ]

        collection_name = "user_uploaded"
        vector_store.index_documents(collection_name, docs)

        return {
            "status": "ok",
            "documents": len(docs),
            "chunks": len(docs),
            "collection": collection_name,
            "filename": file.filename,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.get("/api/verify-citation")
async def verify_citation(surah: int, ayah: int):
    """Verify a Quran citation against AlQuran.cloud API."""
    import requests

    try:
        url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/en.yusufali"
        resp = requests.get(url, timeout=10)

        if resp.status_code == 200:
            data = resp.json()["data"]
            return {
                "verified": True,
                "text": data["text"],
                "surah": data["surah"]["englishName"],
                "surah_number": data["surah"]["number"],
                "ayah_number": data["numberInSurah"],
            }

        return {"verified": False, "error": "Verse not found"}
    except Exception as e:
        return {"verified": False, "error": str(e)}


# =========================
# WEBSOCKET STREAMING
# =========================
@app.websocket("/ws/ask")
async def ws_ask(ws: WebSocket):
    """WebSocket endpoint for streaming answers."""
    await ws.accept()

    try:
        while True:
            data = await ws.receive_json()
            query = data.get("query", "")
            language = data.get("language", "en")

            if not query.strip():
                await ws.send_json({"type": "error", "message": "Empty query"})
                continue

            if graph is not None:
                try:
                    # Stream tokens from RAG pipeline
                    async for event in graph.astream_events(
                        {
                            "query": query,
                            "language": language,
                            "retrieved_docs": {},
                            "routing": [],
                            "iteration": 0,
                        },
                        version="v2",
                    ):
                        if event["event"] == "on_llm_stream":
                            chunk = event["data"].get("chunk", "")
                            if chunk:
                                await ws.send_json({"type": "token", "content": chunk})

                        elif event["event"] == "on_chain_end":
                            output = event.get("data", {}).get("output", {})
                            await ws.send_json({
                                "type": "done",
                                "citation_cards": output.get("citation_cards", []),
                                "citation_valid": output.get("citation_valid", False),
                            })
                    continue
                except Exception as e:
                    logger.error(f"WS RAG error: {e}")
                    # Fall through

            # Fallback: send the fallback answer
            fb = _get_fallback_answer(query)
            for token in fb.answer.split(" "):
                await ws.send_json({"type": "token", "content": token + " "})

            await ws.send_json({
                "type": "done",
                "citation_cards": fb.citation_cards,
                "citation_valid": fb.citation_valid,
            })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await ws.close()
        except Exception:
            pass


# =========================
# MOUNT FRONTEND (after API/WS routes)
# =========================
if FRONTEND_PATH.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_PATH), html=True), name="frontend")
