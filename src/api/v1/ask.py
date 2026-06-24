# src/api/v1/ask.py
"""Tenant-scoped query endpoints (v1)."""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.auth.dependencies import AuthContext, get_auth_context
from src.services.cache_service import cache_get, cache_set

router = APIRouter(tags=["ask"])


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en", pattern="^(en|ar|ur)$")
    sources: list[str] = Field(default_factory=lambda: ["quran", "hadith_bukhari"])
    conversation_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    citations: list[str] = []
    citation_cards: list[dict] = []
    citation_valid: bool = False
    sources_used: list[str] = []
    confidence_score: float = 0.0
    verification_passed: bool = False
    source_types: list[str] = []
    safety_flags: list[str] = []
    language: str = "en"
    conversation_id: str = ""
    follow_up_questions: list[str] = []
    verse_triplets: list[dict] = []
    hallucination_ratio: float = 0.0
    fact_check_passed: bool = True


@router.post("/ask", response_model=AskResponse)
async def ask_v1(
    req: AskRequest,
    auth: Optional[AuthContext] = Depends(get_auth_context),
):
    """Tenant-scoped query endpoint with auth support."""
    # Initialize RAG pipeline
    from src.api.main import _init_rag, graph
    _init_rag()

    if graph is None:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline not available",
        )

    # Check cache
    from src.api.main import _build_conversation_context
    tenant_id = auth.tenant_id if auth else None
    cache_key = f"{req.query}:{req.language}:{','.join(sorted(req.sources))}:{tenant_id}"
    cached = await cache_get(cache_key)
    if cached:
        return AskResponse(**cached)

    # Build conversation context
    augmented_query, conv_id = _build_conversation_context(
        req.conversation_id or "", req.query
    )

    start_time = time.time()

    try:
        result = graph.invoke({
            "query": augmented_query,
            "language": req.language,
            "original_query": req.query,
            "translated_query": augmented_query,
            "response_language": req.language,
            "retrieved_docs": {},
            "routing": req.sources,
            "iteration": 0,
            "conversation_id": conv_id,
            "conversation_history": [],
            "is_followup": bool(req.conversation_id),
        })

        elapsed = time.time() - start_time

        answer = result.get("response", "")
        citations = result.get("citations", [])
        citation_cards = result.get("citation_cards", [])
        citation_valid = result.get("citation_valid", False)
        sources_used = list(result.get("retrieved_docs", {}).keys())

        response = AskResponse(
            answer=answer,
            citations=citations,
            citation_cards=citation_cards,
            citation_valid=citation_valid,
            sources_used=sources_used,
            confidence_score=result.get("confidence_score", 0.0),
            verification_passed=result.get("verification_passed", False),
            source_types=result.get("source_types", []),
            safety_flags=result.get("safety_flags", []),
            language=result.get("response_language", req.language),
            conversation_id=conv_id,
            follow_up_questions=result.get("follow_up_questions", []),
            verse_triplets=result.get("verse_triplets", []),
            hallucination_ratio=result.get("hallucination_ratio", 0.0),
            fact_check_passed=result.get("fact_check_passed", True),
        )

        # Cache response
        await cache_set(cache_key, response.model_dump(), ttl=300)

        return response

    except Exception as e:
        import logging
        logger = logging.getLogger("islamic-rag")
        logger.error(f"v1 ask error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your query",
        )
