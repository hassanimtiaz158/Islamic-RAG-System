from typing import TypedDict, Annotated, Dict, List
import operator


class IslamicAgentState(TypedDict):
    # ── Input ──
    query: str
    query_type: str
    routing: list[str]
    language: str

    # ── Retrieval ──
    retrieved_docs: Annotated[dict, operator.or_]
    retrieval_scores: dict           # {collection: [scores]}
    retrieval_confidence: float      # 0.0 – 1.0 overall retrieval confidence

    # ── Context ──
    context: str
    context_sources: list[str]       # list of source labels in context

    # ── Generation ──
    response: str
    citations: list
    citation_cards: list
    citation_valid: bool

    # ── Verification ──
    verification_passed: bool        # answer verified against context
    unsupported_claims: list[str]    # claims removed during verification
    confidence_score: float          # 0.0 – 1.0 final answer confidence
    safety_flags: list[str]          # e.g., ["scholarly_opinion", "sensitive_topic"]
    source_types: list[str]          # ["quran", "hadith", "tafsir", "scholarly_opinion"]

    # ── Flow control ──
    iteration: int
    insufficient_evidence: bool      # True when retrieval found nothing relevant
