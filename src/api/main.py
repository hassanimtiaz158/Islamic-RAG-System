# src/api/main.py
"""
Islamic Knowledge RAG API — FastAPI application
Provides chat/query, document upload, citation verification, and health check.
SaaS Edition: multi-tenant, auth-ready, Redis-cached.
"""

import asyncio
import os
import threading
import logging
import time
import uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables (override=True so .env changes are picked up on reload)
load_dotenv(override=True)

# ── Logging Configuration ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("islamic-rag")

# ── Environment (legacy — prefer src.config.settings for new code) ──
from src.config.settings import get_settings as _get_settings
_llm_settings = _get_settings()
LLM_PROVIDER = _llm_settings.LLM_PROVIDER
LLM_MODEL = _llm_settings.LLM_MODEL

# ── CORS: allowed origins from env (comma-separated), default to localhost only ──
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000")
ALLOWED_ORIGINS = [o.strip() for o in _allowed_origins.split(",") if o.strip()]

# ── Response cache (simple in-memory) ──
_response_cache: dict = {}
_cache_lock = threading.Lock()
_CACHE_MAX_SIZE = 200
_CACHE_TTL = 300  # seconds


def _cache_get(key: str) -> Optional[dict]:
    """Get cached response if not expired."""
    with _cache_lock:
        if key in _response_cache:
            entry = _response_cache[key]
            if time.time() - entry["ts"] < _CACHE_TTL:
                return entry["data"]
            else:
                del _response_cache[key]
    return None


def _cache_set(key: str, data: dict) -> None:
    """Cache a response with TTL."""
    with _cache_lock:
        if len(_response_cache) >= _CACHE_MAX_SIZE:
            # Evict oldest entry
            oldest_key = min(_response_cache, key=lambda k: _response_cache[k]["ts"])
            del _response_cache[oldest_key]
        _response_cache[key] = {"ts": time.time(), "data": data}


# ── Conversation store (in-memory, TTL-based) ──
_conversation_store: dict = {}  # {conversation_id: {"history": [...], "ts": time}}
_CONV_LOCK = threading.Lock()
_CONV_MAX_SESSIONS = 100
_CONV_TTL = 1800  # 30 minutes


def _get_conversation(conversation_id: str) -> Optional[list]:
    """Get conversation history if session exists and is not expired."""
    with _CONV_LOCK:
        if conversation_id in _conversation_store:
            entry = _conversation_store[conversation_id]
            if time.time() - entry["ts"] < _CONV_TTL:
                return entry["history"]
            else:
                del _conversation_store[conversation_id]
    return None


def _save_conversation(conversation_id: str, history: list) -> None:
    """Save conversation history, evicting oldest if at capacity."""
    with _CONV_LOCK:
        if len(_conversation_store) >= _CONV_MAX_SESSIONS and conversation_id not in _conversation_store:
            oldest_key = min(_conversation_store, key=lambda k: _conversation_store[k]["ts"])
            del _conversation_store[oldest_key]
        _conversation_store[conversation_id] = {"ts": time.time(), "history": history}


def _build_conversation_context(conversation_id: str, current_query: str) -> tuple:
    """
    Build context with conversation history prepended.
    Returns (augmented_query, conversation_id).
    """
    history = _get_conversation(conversation_id) if conversation_id else None

    if not history:
        # New conversation
        new_id = str(uuid.uuid4())[:8]
        return current_query, new_id

    # Build context from last 3 turns
    context_lines = ["[Previous conversation for context:]"]
    for turn in history[-3:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")[:300]  # Truncate long messages
        if role == "user":
            context_lines.append(f"User: {content}")
        else:
            context_lines.append(f"Assistant: {content}")
    context_lines.append("")
    context_lines.append("[Current question:]")
    context_lines.append(current_query)

    return "\n".join(context_lines), conversation_id


# ── RAG dependencies (lazy init) ──
vector_store = None
graph = None
_rag_initialized = False
_rag_error: str = ""
_rag_init_lock = threading.Lock()


def _init_rag():
    """Lazy initialization of the RAG pipeline."""
    global vector_store, graph, _rag_initialized, _rag_error
    # Hold the lock across the entire check-and-initialize window so concurrent
    # requests cannot both initialize the pipeline / Chroma client.
    with _rag_init_lock:
        if _rag_initialized:
            return
        try:
            from src.core.islamic_vectorDB import IslamicVectorStore
            from src.agents.islamic_graph import build_islamic_graph

            vector_store = IslamicVectorStore()
            graph = build_islamic_graph(vector_store)
            _rag_initialized = True
            _rag_error = ""
            logger.info("RAG pipeline initialized successfully")
        except Exception as e:
            _rag_error = str(e)
            logger.error(f"RAG pipeline initialization failed: {e}", exc_info=True)
            logger.warning("Using fallback demo mode.")


# =========================
# APP SETUP
# =========================
app = FastAPI(
    title="Al-Ilm — Islamic Knowledge RAG API",
    version="2.0.0",
    description="AI-powered Islamic knowledge chatbot with source-backed answers from Quran, Hadith, and Tafsir.",
)

# ── Middleware Stack (order matters: outermost first) ──
from src.middleware.security import SecurityHeadersMiddleware
from src.middleware.error_handling import ErrorHandlingMiddleware
from src.middleware.tenant import TenantMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(TenantMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── API v1 Router (SaaS endpoints) ──
from src.api.v1 import v1_router
app.include_router(v1_router)

# Frontend path
FRONTEND_PATH = Path(__file__).resolve().parent.parent.parent / "frontend"


# =========================
# REQUEST/RESPONSE MODELS
# =========================
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User's question about Islam")
    language: str = Field(default="en", pattern="^(en|ar|ur)$")
    sources: list[str] = Field(default_factory=lambda: ["quran", "hadith_bukhari"])
    conversation_id: str = Field(default="", description="Optional conversation session ID for multi-turn chat")


class QueryResponse(BaseModel):
    answer: str
    citations: list[str] = []
    citation_cards: list[dict] = []
    citation_valid: bool = False
    sources_used: list[str] = []
    confidence_score: float = 0.0
    verification_passed: bool = False
    source_types: list[str] = []
    safety_flags: list[str] = []
    retrieval_confidence: float = 0.0
    insufficient_evidence: bool = False
    # Multilingual fields
    language: str = "en"
    original_query: str = ""
    translated_query: str = ""
    response_language: str = "en"
    # New fields (Phase 5)
    conversation_id: str = ""
    follow_up_questions: list[str] = []
    verse_triplets: list[dict] = []
    hallucination_ratio: float = 0.0
    fact_check_passed: bool = True


class HealthResponse(BaseModel):
    status: str
    rag_available: bool
    rag_error: str = ""
    llm_provider: str
    llm_model: str
    version: str = "2.0.0"
    collections: dict = {}


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
        "answer": 'The majority of Islamic scholars hold that musical instruments (except the duff/hand drum at weddings) are prohibited. Allah says: "And of the people is he who buys the amusement of speech to mislead from the way of Allah without knowledge and who takes it in ridicule." [Quran Luqman 31:6]\n\nThe Prophet ﷺ said: "There will be among my nation people who will make permissible fornication, silk, alcohol, and musical instruments." [Bukhari 5590]\n\nHowever, the duff (hand drum) is permitted at weddings and Eid celebrations. [Tirmidhi 1089]\n\n⚠️ **Important Note:** This topic involves nuanced Islamic rulings. The information above is based on the retrieved sources. For personal religious obligations, please consult a qualified Islamic scholar.',
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
        "answer": 'Charity (Sadaqah) is deeply encouraged in Islam beyond the obligatory Zakat. Allah says: "The example of those who spend their wealth in the way of Allah is like a seed of grain which grows seven spikes; in each spike is a hundred grains." [Quran Al-Baqarah 2:261]\n\nThe Prophet ﷺ said: "Charity does not decrease wealth." [Muslim 2588]\n\nHe also said: "Every act of goodness is charity. Smiling at your brother is charity. A good word is charity. Every step you take toward prayer is charity. Removing a harmful object from the road is charity." [Muslim 1009]',
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

# ═══════════════════════════════════════════════
# MULTILINGUAL FALLBACK ANSWERS (Phase 4)
# ═══════════════════════════════════════════════
FALLBACK_NOT_FOUND = {
    "en": (
        "I could not find sufficient evidence in the available Islamic sources "
        "to answer this question. Please try rephrasing your question or "
        "selecting additional sources. For specific Islamic rulings, "
        "please consult a qualified Islamic scholar."
    ),
    "ar": (
        "لم أتمكن من العثور على أدلة كافية في المصادر الإسلامية المتاحة "
        "للإجابة على هذا السؤال. يرجى إعادة صياغة سؤالك أو اختيار مصادر إضافية. "
        "للأحكام الإسلامية المحددة، يرجى استشارة عالم إسلامي مؤهل."
    ),
    "ur": (
        "میں دستیاب اسلامی ذرائع میں اس سوال کا جواب دینے کے لیے کافی دلیل "
        "نہیں ڈھونڈ سکا۔ براہ کرم اپنا سوال دوبارہ لکھیں یا مزید ذرائع منتخب کریں۔ "
        "مخصوص اسلامی احکام کے لیے، براہ کرم ایک مستند اسلامی عالم سے مشورہ کریں۔"
    ),
}


def _get_fallback_response(query: str, language: str = "en") -> QueryResponse:
    """Generate a response from the curated fallback knowledge base."""
    q = query.lower()

    # Score each entry by keyword matches
    best_score = 0
    best_entry = None

    for key, entry in FALLBACK_ANSWERS.items():
        score = sum(1 for kw in key.split() if kw in q)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score > 0 and best_entry:
        return QueryResponse(
            answer=best_entry["answer"],
            citations=best_entry["citations"],
            citation_cards=FALLBACK_CITATION_CARDS,
            citation_valid=True,
            sources_used=["quran", "hadith_bukhari"],
            confidence_score=0.5,
            verification_passed=True,
            source_types=["quran", "hadith"],
            safety_flags=[],
            retrieval_confidence=0.3,
            insufficient_evidence=False,
            language=language,
            original_query=query,
            response_language=language,
        )

    not_found_msg = FALLBACK_NOT_FOUND.get(language, FALLBACK_NOT_FOUND["en"])
    return QueryResponse(
        answer=not_found_msg,
        citations=[],
        citation_cards=[],
        citation_valid=False,
        sources_used=[],
        confidence_score=0.0,
        verification_passed=False,
        source_types=["none"],
        safety_flags=[],
        retrieval_confidence=0.0,
        insufficient_evidence=True,
        language=language,
        original_query=query,
        response_language=language,
    )


# =========================
# REST API ENDPOINTS
# =========================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with collection info."""
    collections_info = {}
    if vector_store is not None:
        try:
            for col_name in vector_store.list_collections():
                count = vector_store.get_collection_count(col_name)
                collections_info[col_name] = count
        except Exception:
            pass

    return HealthResponse(
        status="ok",
        rag_available=graph is not None,
        rag_error=_rag_error,
        llm_provider=LLM_PROVIDER,
        llm_model=LLM_MODEL,
        version="2.0.0",
        collections=collections_info,
    )


@app.post("/api/ask", response_model=QueryResponse)
async def ask_islamic(req: QueryRequest):
    """
    Main chat endpoint.
    Uses the RAG pipeline if available, otherwise falls back to curated knowledge.
    """
    _init_rag()

    # Check cache
    cache_key = f"{req.query}:{req.language}:{','.join(sorted(req.sources))}"
    cached = _cache_get(cache_key)
    if cached:
        logger.info(f"Cache hit for query: {req.query[:50]}...")
        return QueryResponse(**cached)

    if graph is not None:
        try:
            start_time = time.time()

            # Build conversation context
            augmented_query, conv_id = _build_conversation_context(
                req.conversation_id, req.query
            )

            # Always include user-uploaded documents so uploaded files are
            # retrievable (the classifier only routes to shared collections).
            routing = list(req.sources)
            if "user_uploaded" not in routing:
                routing.append("user_uploaded")

            result = graph.invoke({
                "query": augmented_query,
                "language": req.language,
                "original_query": req.query,
                "translated_query": augmented_query,
                "response_language": req.language,
                "retrieved_docs": {},
                "routing": routing,
                "iteration": 0,
                "conversation_id": conv_id,
                "conversation_history": [],
                "is_followup": bool(req.conversation_id),
            })

            elapsed = time.time() - start_time
            logger.info(f"RAG query completed in {elapsed:.2f}s")

            answer = result.get("response", "")
            citations = result.get("citations", [])
            # Citations are now full dicts internally; the response model
            # expects a list of raw citation strings.
            citations = [c["raw"] if isinstance(c, dict) else c for c in citations]
            citation_cards = result.get("citation_cards", [])
            citation_valid = result.get("citation_valid", False)
            sources_used = list(result.get("retrieved_docs", {}).keys())

            # Save conversation turn
            history = _get_conversation(conv_id) or []
            history.append({"role": "user", "content": req.query})
            history.append({"role": "assistant", "content": answer[:500]})
            _save_conversation(conv_id, history)

            response = QueryResponse(
                answer=answer,
                citations=citations,
                citation_cards=citation_cards,
                citation_valid=citation_valid,
                sources_used=sources_used,
                confidence_score=result.get("confidence_score", 0.0),
                verification_passed=result.get("verification_passed", False),
                source_types=result.get("source_types", []),
                safety_flags=result.get("safety_flags", []),
                retrieval_confidence=result.get("retrieval_confidence", 0.0),
                insufficient_evidence=result.get("insufficient_evidence", False),
                language=result.get("response_language", req.language),
                original_query=result.get("original_query", req.query),
                translated_query=result.get("translated_query", augmented_query),
                response_language=result.get("response_language", req.language),
                conversation_id=conv_id,
                follow_up_questions=result.get("follow_up_questions", []),
                verse_triplets=result.get("verse_triplets", []),
                hallucination_ratio=result.get("hallucination_ratio", 0.0),
                fact_check_passed=result.get("fact_check_passed", True),
            )

            # Cache the response
            _cache_set(cache_key, response.model_dump())

            return response

        except Exception as e:
            logger.error(f"RAG pipeline error: {e}", exc_info=True)
            # Fall through to fallback

    return _get_fallback_response(req.query, req.language)


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt"}
MAX_FILENAME_LENGTH = 200


def _sanitize_filename(filename: Optional[str]) -> str:
    """Sanitize uploaded filename to prevent injection attacks."""
    import re
    if not filename:
        return "untitled"
    # Remove path separators and null bytes
    filename = filename.replace("\\", "").replace("/", "").replace("\x00", "")
    # Strip leading dots (hidden files)
    filename = filename.lstrip(".")
    # Allow only safe characters
    filename = re.sub(r"[^\w\s\-.]", "_", filename)
    # Truncate
    filename = filename[:MAX_FILENAME_LENGTH]
    return filename or "untitled"


@app.post("/api/index-document")
async def index_document(file: UploadFile = File(...)):
    """Upload and index an Islamic text document (PDF or TXT)."""
    _init_rag()
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail="Vector store is not available. Please configure the RAG pipeline first.",
        )

    # Validate file extension
    original_filename = _sanitize_filename(file.filename)
    if original_filename.lower().endswith(".pdf"):
        ext = ".pdf"
    elif original_filename.lower().endswith(".txt"):
        ext = ".txt"
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only .pdf and .txt files are allowed.",
        )

    try:
        content = await file.read()

        # Limit file size (50MB)
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

        text = None
        if ext == ".pdf":
            # Validate PDF magic bytes
            if not content[:5].startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid PDF file. The file does not appear to be a valid PDF.",
                )
            try:
                import fitz  # PyMuPDF
                with fitz.open(stream=content, filetype="pdf") as doc:
                    text = "\n\n".join(page.get_text() for page in doc)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to extract text from PDF. Try uploading a .txt file.",
                )
        else:
            text = content.decode("utf-8", errors="replace")

        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="No text content found in the uploaded file.")

        from langchain_core.documents import Document

        # Chunk by paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        docs = [
            Document(
                page_content=p,
                metadata={
                    "source": "user_upload",
                    "filename": original_filename,
                    "citation": f"[Uploaded: {original_filename}]",
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
            "filename": original_filename,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indexing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Indexing failed due to an internal error.")


# Surah ayah count limits (module-level constant to avoid per-request allocation)
AYAH_LIMITS = {
    1: 7, 2: 286, 3: 200, 4: 176, 5: 120, 6: 165, 7: 206, 8: 75, 9: 129, 10: 109,
    11: 123, 12: 111, 13: 43, 14: 52, 15: 99, 16: 128, 17: 111, 18: 110, 19: 98, 20: 135,
    21: 112, 22: 78, 23: 118, 24: 64, 25: 77, 26: 227, 27: 93, 28: 88, 29: 69, 30: 60,
    31: 34, 32: 30, 33: 73, 34: 54, 35: 85, 36: 83, 37: 182, 38: 88, 39: 75, 40: 85,
    41: 54, 42: 53, 43: 89, 44: 59, 45: 37, 46: 35, 47: 38, 48: 29, 49: 18, 50: 45,
    51: 60, 52: 49, 53: 62, 54: 55, 55: 78, 56: 96, 57: 29, 58: 22, 59: 24, 60: 14,
    61: 14, 62: 11, 63: 11, 64: 18, 65: 12, 66: 12, 67: 30, 68: 52, 69: 52, 70: 44,
    71: 28, 72: 28, 73: 20, 74: 56, 75: 40, 76: 31, 77: 50, 78: 40, 79: 46, 80: 42,
    81: 29, 82: 19, 83: 36, 84: 25, 85: 22, 86: 17, 87: 19, 88: 62, 89: 30, 90: 20,
    91: 15, 92: 21, 93: 11, 94: 8, 95: 8, 96: 19, 97: 5, 98: 88, 99: 83, 100: 111,
    101: 11, 102: 8, 103: 9, 104: 7, 105: 5, 106: 4, 107: 7, 108: 3, 109: 6, 110: 6,
    111: 5, 112: 4, 113: 5, 114: 6,
}


@app.get("/api/verify-citation")
async def verify_citation(surah: int = Query(..., ge=1, le=114), ayah: int = Query(..., ge=1, le=286)):
    """Verify a Quran citation and return Arabic + English text."""
    max_ayahs = AYAH_LIMITS.get(surah, 286)
    if ayah > max_ayahs:
        return {"verified": False, "error": f"Surah {surah} has only {max_ayahs} ayahs"}

    try:
        import httpx
        arabic_url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}"
        english_url = f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/en.yusufali"

        async with httpx.AsyncClient(timeout=10) as client:
            arabic_resp, english_resp = await asyncio.gather(
                client.get(arabic_url),
                client.get(english_url),
            )

        result = {"verified": False}

        if arabic_resp.status_code == 200:
            arabic_data = arabic_resp.json()["data"]
            result["verified"] = True
            result["arabic"] = arabic_data["text"]
            result["surah"] = arabic_data["surah"]["englishName"]
            result["surah_number"] = arabic_data["surah"]["number"]
            result["ayah_number"] = arabic_data["numberInSurah"]

        if english_resp.status_code == 200:
            english_data = english_resp.json()["data"]
            result["english"] = english_data["text"]

        if not result["verified"]:
            result["error"] = "Verse not found"
        return result

    except httpx.TimeoutException:
        logger.warning(f"verify-citation timeout for {surah}:{ayah}")
        return {"verified": False, "error": "External API request timed out"}
    except httpx.ConnectError:
        logger.warning(f"verify-citation connection error for {surah}:{ayah}")
        return {"verified": False, "error": "Could not reach external API"}
    except Exception as e:
        logger.error(f"verify-citation error: {e}", exc_info=True)
        return {"verified": False, "error": "An internal error occurred"}


class TranslateVerseRequest(BaseModel):
    text: str = Field(default="", description="Text to translate")
    target_lang: str = Field(default="ur", description="Target language code (ur/ar)")


@app.post("/api/translate-verse")
async def translate_verse(req: TranslateVerseRequest):
    """Translate verse text to Urdu or Arabic using the LLM."""
    if not req.text or req.target_lang not in ("ur", "ar"):
        return {"translated": req.text}

    try:
        from src.agents.islamic_graph import _get_llm
        from src.utils.translator import translate_text

        llm = _get_llm()
        translated = translate_text(req.text, "en", req.target_lang, llm)
        return {"translated": translated}
    except Exception as e:
        logger.warning(f"Verse translation failed: {e}")
        return {"translated": req.text, "error": str(e)}


# =========================
# WEBSOCKET STREAMING
# =========================
# Per-connection rate limiter state
_WS_RATE_LIMIT = 10  # max messages per window
_WS_RATE_WINDOW = 10  # seconds


@app.websocket("/ws/ask")
async def ws_ask(ws: WebSocket):
    """WebSocket endpoint for streaming answers."""
    await ws.accept()
    _init_rag()

    # Rate limiting state
    _msg_timestamps: list = []

    try:
        while True:
            # Enforce rate limit
            now = time.time()
            _msg_timestamps = [t for t in _msg_timestamps if now - t < _WS_RATE_WINDOW]
            if len(_msg_timestamps) >= _WS_RATE_LIMIT:
                await ws.send_json({
                    "type": "error",
                    "message": f"Rate limit exceeded. Max {_WS_RATE_LIMIT} messages per {_WS_RATE_WINDOW}s.",
                })
                await ws.close()
                break
            _msg_timestamps.append(now)

            data = await ws.receive_json()
            query = data.get("query", "")
            language = data.get("language", "en")

            if not query.strip():
                await ws.send_json({"type": "error", "message": "Empty query"})
                continue

            if len(query) > 2000:
                await ws.send_json({"type": "error", "message": "Query too long. Maximum 2000 characters."})
                continue

            if graph is not None:
                try:
                    ws_conversation_id = data.get("conversation_id", "")
                    augmented_query, conv_id = _build_conversation_context(
                        ws_conversation_id, query
                    )

                    # Run the pipeline once and stream word-by-word
                    ws_routing = list(data.get("sources", ["quran", "hadith_bukhari"]))
                    if "user_uploaded" not in ws_routing:
                        ws_routing.append("user_uploaded")
                    final_output = graph.invoke({
                        "query": augmented_query,
                        "language": language,
                        "original_query": query,
                        "translated_query": augmented_query,
                        "response_language": language,
                        "retrieved_docs": {},
                        "routing": ws_routing,
                        "iteration": 0,
                        "conversation_id": conv_id,
                        "conversation_history": [],
                        "is_followup": bool(ws_conversation_id),
                    })
                    # Stream the response word-by-word for real-time feel
                    answer_text = final_output.get("response", "")
                    for word in answer_text.split(" "):
                        await ws.send_json({"type": "token", "content": word + " "})
                    if answer_text:
                        await ws.send_json({"type": "token", "content": "\n"})

                    # Save conversation
                    history = _get_conversation(conv_id) or []
                    history.append({"role": "user", "content": query})
                    history.append({"role": "assistant", "content": final_output.get("response", "")[:500]})
                    _save_conversation(conv_id, history)

                    await ws.send_json({
                        "type": "done",
                        "citation_cards": final_output.get("citation_cards", []),
                        "citation_valid": final_output.get("citation_valid", False),
                        "confidence_score": final_output.get("confidence_score", 0.0),
                        "verification_passed": final_output.get("verification_passed", False),
                        "source_types": final_output.get("source_types", []),
                        "safety_flags": final_output.get("safety_flags", []),
                        "follow_up_questions": final_output.get("follow_up_questions", []),
                        "verse_triplets": final_output.get("verse_triplets", []),
                        "conversation_id": conv_id,
                        "hallucination_ratio": final_output.get("hallucination_ratio", 0.0),
                        "fact_check_passed": final_output.get("fact_check_passed", True),
                    })
                    continue
                except Exception as e:
                    logger.error(f"WS RAG error: {e}")

            # Fallback
            fb = _get_fallback_response(query)
            for token in fb.answer.split(" "):
                await ws.send_json({"type": "token", "content": token + " "})

            await ws.send_json({
                "type": "done",
                "citation_cards": fb.citation_cards,
                "citation_valid": fb.citation_valid,
                "confidence_score": fb.confidence_score,
                "verification_passed": fb.verification_passed,
                "source_types": fb.source_types,
                "safety_flags": fb.safety_flags,
                "conversation_id": data.get("conversation_id", ""),
            })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await ws.close()
        except Exception:
            pass


# =========================
# MOUNT FRONTEND
# =========================
if FRONTEND_PATH.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_PATH), html=True), name="frontend")
