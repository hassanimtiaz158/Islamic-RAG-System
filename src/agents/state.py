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

    # ── Translation ──
    original_query: str              # user's original query (before translation)
    translated_query: str            # English version used for retrieval
    response_language: str           # target language for the response (en/ar/ur)

    # ── Fact-checking ──
    citation_verdicts: list[dict]    # per-citation verdicts from fact_check node
    hallucination_ratio: float       # 0.0 (none) to 1.0 (all fabricated)
    fact_check_passed: bool          # True if hallucination_ratio < 0.5

    # ── Follow-up questions ──
    follow_up_questions: list[str]   # suggested next questions

    # ── Conversation ──
    conversation_id: str             # UUID for the conversation session
    conversation_history: list[dict] # [{role: "user"|"assistant", content: str}]
    is_followup: bool                # True if this query references prior context

    # ── Verse triplets ──
    verse_triplets: list[dict]       # Arabic/English/Urdu verse data for frontend

    # ── Flow control ──
    iteration: int
    insufficient_evidence: bool      # True when retrieval found nothing relevant
    include_followups: bool          # If True, runs suggest_followups LLM call (adds latency); default False via .get()
