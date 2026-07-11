# src/agents/islamic_graph.py

import os
import json
import logging
import re
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from src.agents.state import IslamicAgentState
from src.core.islamic_vectorDB import IslamicVectorStore
from src.agents.classifier import classifier_node
from src.utils.citation_engine import (
    extract_citations,
    format_citation_cards,
    enforce_citations,
    verify_answer_grounding,
    check_islamic_safety,
    cross_reference_citations,
    build_verse_triplets,
)
from src.utils.translator import translate_query_to_english, translate_response_to_language

load_dotenv(override=True)
logger = logging.getLogger("islamic-rag")


# ═══════════════════════════════════════════════
# MODEL INITIALIZATION (supports groq, openai, ollama, anthropic)
# ═══════════════════════════════════════════════
def _get_llm():
    """Get an LLM based on LLM_PROVIDER env var.

    Falls back to a local Ollama instance in development when the
    configured provider has no API key set.
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    env = os.getenv("ENVIRONMENT", "development").lower()

    def _try_ollama_fallback():
        """Attempt to use local Ollama as a dev fallback."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            from langchain_ollama import ChatOllama
            fallback_model = os.getenv("LLM_MODEL", "phi3:latest")
            logger.warning(
                f"No API key for {provider} — falling back to Ollama ({fallback_model})"
            )
            return ChatOllama(model=fallback_model, base_url=base_url, temperature=0.0)
        except Exception as e:
            raise RuntimeError(
                f"No API key for {provider} and Ollama fallback failed: {e}"
            )

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            if env != "production":
                return _try_ollama_fallback()
            raise RuntimeError(
                "GROQ_API_KEY is required. "
                "Get a free key at https://console.groq.com and set it in .env"
            )
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(model=model, temperature=0.0, groq_api_key=api_key)
        except ImportError:
            raise RuntimeError("langchain-groq not installed. Run: pip install langchain-groq")
        except Exception as e:
            raise RuntimeError(f"Groq LLM init failed: {e}")

    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            if env != "production":
                return _try_ollama_fallback()
            raise RuntimeError("OPENAI_API_KEY is required. Set it in .env")
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model, temperature=0.0, openai_api_key=api_key)
        except ImportError:
            raise RuntimeError("langchain-openai not installed. Run: pip install langchain-openai")
        except Exception as e:
            raise RuntimeError(f"OpenAI LLM init failed: {e}")

    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            from langchain_ollama import ChatOllama
            return ChatOllama(model=model, base_url=base_url, temperature=0.0)
        except ImportError:
            raise RuntimeError("langchain-ollama not installed. Run: pip install langchain-ollama")
        except Exception as e:
            raise RuntimeError(f"Ollama LLM init failed: {e}")

    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            if env != "production":
                return _try_ollama_fallback()
            raise RuntimeError("ANTHROPIC_API_KEY is required. Set it in .env")
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model, temperature=0.0, anthropic_api_key=api_key)
        except ImportError:
            raise RuntimeError("langchain-anthropic not installed. Run: pip install langchain-anthropic")
        except Exception as e:
            raise RuntimeError(f"Anthropic LLM init failed: {e}")

    else:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER: '{provider}'. Supported: groq, openai, ollama, anthropic"
        )


# ═══════════════════════════════════════════════
# ISLAMIC TERM TRANSLITERATION MAP
# Maps common romanized Urdu/Arabic terms to their English equivalents
# so users can search using familiar terms like "namaz", "zakat", "wudu"
# and still match English content in the vector store.
# ═══════════════════════════════════════════════
ISLAMIC_TERM_MAP = {
    # Prayer & Worship
    "namaz": "prayer salah",
    "salah": "prayer salah",
    "salat": "prayer salah",
    "wudu": "ablution wudu",
    "wuzu": "ablution wudu",
    "ghusl": "bath purification",
    "tayammum": "dry ablution",
    "adhan": "call to prayer",
    "azaan": "call to prayer",
    "iqamah": "iqamah prayer call",
    "jumuah": "friday prayer",
    "jummah": "friday prayer",
    "eid": "eid prayer festival",
    "taraweeh": "taraweeh night prayer",
    "tahajjud": "night prayer",
    "sujood": "prostration",
    "ruku": "bowing prayer",
    "qiblah": "direction of prayer",
    # Pillars & Charity
    "zakat": "zakat charity",
    "zakah": "zakat charity",
    "sadaqah": "voluntary charity",
    "sadqa": "charity",
    "khums": "khums one-fifth",
    "ushr": "ushr tithe",
    # Fasting
    "roza": "fasting",
    "rozah": "fasting",
    "sawm": "fasting",
    "iftar": "breaking fast",
    "sehri": "pre-dawn meal fasting",
    "suhoor": "pre-dawn meal fasting",
    "tawaf": "circumambulation kaaba",
    "hajj": "pilgrimage hajj",
    "umrah": "umrah pilgrimage",
    # Faith & Theology
    "iman": "faith belief",
    "tawhid": "monotheism oneness of God",
    "shirk": "polytheism associating with God",
    "kufr": "disbelief",
    "nifaq": "hypocrisy",
    "tawbah": "repentance",
    "istighfar": "seeking forgiveness",
    "shukr": "gratitude",
    "sabr": "patience",
    "tawakkul": "trust in God",
    "khushu": "humility in prayer",
    # Quran & Hadith
    "quran": "Quran",
    "surah": "surah chapter",
    "ayat": "verses",
    "ayah": "verse",
    "hadith": "hadith prophetic tradition",
    "sunnah": "sunnah prophetic practice",
    "dua": "supplication prayer",
    "duaa": "supplication prayer",
    "dhikr": "remembrance of God",
    "tasbih": "glorification of God",
    # Fiqh / Purity
    "halal": "permissible",
    "haram": "prohibited",
    "makruh": "disliked",
    "mustahabb": "recommended",
    "wajib": "obligatory",
    "fard": "obligatory",
    "nafl": "voluntary prayer",
    "janabat": "ritual impurity",
    "haydh": "menstruation",
    # Food & Drink
    "halal food": "permissible food",
    "haram food": "prohibited food",
    "zabihah": "slaughtered meat",
    "dhabihah": "slaughtered meat",
    # General
    "rasool": "messenger prophet",
    "rasul": "messenger prophet",
    "sallallahu alayhi wasallam": "peace be upon him",
    "pbuh": "peace be upon him",
    "alayhis salaam": "peace be upon him",
    "radiyallahu anhu": "may Allah be pleased with him",
    "inshallah": "if Allah wills",
    "inshaallah": "if Allah wills",
    "mashallah": "what Allah has willed",
    "alhamdulillah": "praise be to Allah",
    "bismillah": "in the name of Allah",
    "subhanallah": "glory be to Allah",
    "allahu akbar": "Allah is the greatest",
    "jazakallah": "may Allah reward you",
    "astaghfirullah": "I seek forgiveness from Allah",
}


def _normalize_islamic_terms(query: str) -> str:
    """
    Replace common romanized Islamic terms in a query with their English equivalents.
    Uses whole-word matching to avoid false substitutions.
    Works regardless of the user's selected language (en/ar/ur).
    Deduplicates overlapping expansions so "namaz" → "prayer salah"
    doesn't compound with "salah" already being replaced.
    """
    if not query.strip():
        return query

    normalized = query.lower()

    # Sort terms by length (longest first) so we match "salah" before "sala"
    # and prevent partial re-matching against already-replaced text.
    sorted_terms = sorted(ISLAMIC_TERM_MAP.keys(), key=len, reverse=True)

    # Track character positions that have already been replaced
    # Strategy: replace with placeholder first, then substitute at the end
    placeholders = {}
    placeholder_idx = 0
    for term in sorted_terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        placeholder = f"\x00ISAIDX{placeholder_idx}\x00"
        placeholders[placeholder] = ISLAMIC_TERM_MAP[term]
        normalized = re.sub(pattern, placeholder, normalized)
        placeholder_idx += 1

    # Now replace placeholders with the actual English expansions
    for placeholder, english in placeholders.items():
        normalized = normalized.replace(placeholder, " " + english + " ")

    # Clean up multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    # De-duplicate consecutive identical words ("prayer prayer" → "prayer")
    words = normalized.split()
    deduped = []
    for w in words:
        if not deduped or w != deduped[-1]:
            deduped.append(w)

    return " ".join(deduped)


# ═══════════════════════════════════════════════
# LANGUAGE INSTRUCTIONS (for synthesis prompt)
# ═══════════════════════════════════════════════
LANGUAGE_INSTRUCTIONS = {
    "en": "",
    "ar": """
═══════════════════════════════════════
LANGUAGE INSTRUCTION — ARABIC
═══════════════════════════════════════
- Respond in formal Modern Standard Arabic (الفصحى)
- Use Arabic script for all text
- Keep Quran verses in their original Arabic text
- Keep Hadith references in their original Arabic text with translation
- Use Arabic punctuation: ، for commas, ؛ for semicolons, ۔ for periods
- Maintain citation format in brackets: [القرآن ...], [البخاري ...], [مسلم ...]
""",
    "ur": """
═══════════════════════════════════════
LANGUAGE INSTRUCTION — URDU
═══════════════════════════════════════
- Respond in Urdu (اردو)
- Use Nastaliq-style Urdu script for all text
- Keep Quran verses in their original Arabic script (with Urdu translation in parentheses if needed)
- Keep Hadith text in Arabic with Urdu explanation
- Maintain citation format in brackets: [قرآن ...], [بخاری ...], [مسلم ...]
- Use Urdu punctuation: ، for commas, ۔ for periods
""",
}


# ═══════════════════════════════════════════════
# SYNTHESIS PROMPT — ZERO-HALLUCINATION
# ═══════════════════════════════════════════════
SYNTHESIS_PROMPT = """\
You are Al-Ilm, an Islamic knowledge assistant. Answer the question using ONLY the provided Islamic sources.

═══════════════════════════════════════
OUTPUT FORMAT — FOLLOW EXACTLY
═══════════════════════════════════════

Structure your answer using these sections (ONLY include sections that have supporting sources — omit sections with no data):

## Summary
[2-3 sentence direct answer to the question]

## From the Quran
[Each point with a citation — use exact citation format below]

## From the Hadith
[Each point with a citation — use exact citation format below]

## Practical Guidance
[What Muslims should do based on these sources]

## Key Takeaways
[2-4 bullet points summarizing the core teachings]

═══════════════════════════════════════
CITATION RULES — ZERO TOLERANCE
═══════════════════════════════════════

1. EXACT FORMAT (DO NOT MODIFY):
   Quran:     [Quran SurahName Chapter:Verse]
              Example: [Quran Al-Baqarah 2:153]

   Hadith:    [Collection Number] or [Collection Chapter, No. Number]
              Examples: [Bukhari 1469]  [Bukhari, Book of Fasting, No. 1985]
                        [Muslim 2999]   [Abu Dawud 45]
                        [Tirmidhi 1089] [Nasai 1234]  [Ibn Majah 567]

   Tafsir:    [Tafsir Source Reference]
              Example: [Tafsir Ibn Kathir 2:153]

2. EVERY factual sentence MUST end with a citation.
   • If you cannot cite it, DELETE the entire sentence.
   • NEVER write citation ranges like "Ayah:2-3".
   • NEVER use parentheses inside citations.

3. INSUFFICIENT SOURCES → ADMIT IT
   If sources lack information, write:
   "I could not find sufficient evidence in the available Islamic sources."
   Do NOT guess or fabricate.

4. SAFETY
   • NEVER invent Quran/Hadith references.
   • For sensitive rulings, add: "Please consult a qualified Islamic scholar."
{language_instructions}
═══════════════════════════════════════
RETRIEVED ISLAMIC SOURCES
═══════════════════════════════════════
{context}

═══════════════════════════════════════
QUESTION
═══════════════════════════════════════
{query}

═══════════════════════════════════════
STRUCTURED ANSWER:
═══════════════════════════════════════
"""


def _build_context_with_citations(retrieved_docs: dict) -> tuple:
    """
    Build context string from retrieved documents, ensuring each chunk
    includes its citation metadata.

    Returns: (context_string, list_of_source_labels)
    """
    context_blocks = []
    source_labels = []

    for col, docs in sorted(retrieved_docs.items()):
        for doc in docs:
            citation = doc.get("citation", "")
            text = doc.get("text", "")

            if not text.strip():
                continue

            block = f"[{col.upper()}]"
            if citation:
                block += f" {citation}"
            block += f"\n{text}"
            context_blocks.append(block)
            source_labels.append(col)

    return "\n\n".join(context_blocks), source_labels


# ═══════════════════════════════════════════════
# QUERY TRANSLATION NODE (NEW — PHASE 4)
# ═══════════════════════════════════════════════
def translate_query_node(llm):
    """
    Translates non-English queries to English for vector search.
    Also normalizes romanized Islamic terms (e.g. "namaz" → "prayer salah")
    in ALL queries regardless of language, so users can use familiar terms.

    The vector store has English content, so non-English queries must be
    translated first. Romanized Islamic terms in English queries are also mapped
    to their English equivalents.
    """
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        language = state.get("language", "en")
        original_query = state.get("query", "")

        if not original_query.strip():
            return {
                "original_query": original_query,
                "translated_query": original_query,
            }

        normalized_query = _normalize_islamic_terms(original_query)

        if language == "en":
            # For English queries, only apply term normalization (no LLM call)
            return {
                "original_query": original_query,
                "translated_query": normalized_query,
            }

        # For non-English queries, normalize terms first then translate via LLM
        try:
            translated = translate_query_to_english(normalized_query, language, llm)
            logger.info(
                f"Query translated ({language} → en): "
                f"'{original_query[:60]}' → '{translated[:60]}'"
            )
            return {
                "original_query": original_query,
                "translated_query": translated,
            }
        except Exception as e:
            logger.warning(f"Query translation failed: {e}. Using normalized query.")
            return {
                "original_query": original_query,
                "translated_query": normalized_query,
            }

    return node


# ═══════════════════════════════════════════════
# RESPONSE TRANSLATION NODE (NEW — PHASE 4)
# ═══════════════════════════════════════════════
def translate_response_node(llm):
    """
    Translates the English response back to the user's selected language.
    Preserves citations and Islamic terminology.
    """
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        language = state.get("language", "en")
        response = state.get("response", "")

        if language == "en" or not response.strip():
            return {
                "response": response,
                "response_language": language,
            }

        try:
            translated = translate_response_to_language(response, language, llm)
            logger.info(
                f"Response translated (en → {language}): "
                f"{len(response)} chars → {len(translated)} chars"
            )
            return {
                "response": translated,
                "response_language": language,
            }
        except Exception as e:
            logger.warning(f"Response translation failed: {e}. Using English response.")
            return {
                "response": response,
                "response_language": "en",
            }

    return node


# ═══════════════════════════════════════════════
# UNIFIED RETRIEVER NODE (ENHANCED)
# ═══════════════════════════════════════════════
def unified_retriever_node(vector_store: IslamicVectorStore):
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        results = {}
        all_scores = {}

        routing = state.get("routing", ["quran", "hadith_bukhari"])
        # Use translated query for retrieval if available
        query = state.get("translated_query", state.get("query", ""))

        logger.info(f"Retrieving from collections: {routing} with query: '{query[:60]}...'")

        for col in routing:
            try:
                scored_docs = vector_store.retrieve_with_scores(
                    col, query=query, k=5
                )

                results[col] = []
                all_scores[col] = []

                for doc, score in scored_docs:
                    results[col].append({
                        "text": doc.page_content,
                        "citation": doc.metadata.get("citation", ""),
                        "score": round(score, 3),
                        "metadata": doc.metadata,
                    })
                    all_scores[col].append(score)

                logger.info(
                    f"[{col}] Retrieved {len(results[col])} docs, "
                    f"scores: {[round(s, 3) for s in all_scores[col]]}"
                )

            except Exception as e:
                logger.warning(f"Retrieval failed for {col}: {e}")
                results[col] = []
                all_scores[col] = []

        # Compute retrieval confidence
        retrieval_confidence = vector_store.compute_retrieval_confidence(
            {col: [(None, s) for s in scores] for col, scores in all_scores.items() if scores}
        )

        total_docs = sum(len(docs) for docs in results.values())
        insufficient = total_docs == 0 or retrieval_confidence < 0.2

        if insufficient:
            logger.warning(
                f"Insufficient retrieval: {total_docs} docs, "
                f"confidence: {retrieval_confidence:.3f}"
            )

        return {
            "retrieved_docs": results,
            "retrieval_scores": all_scores,
            "retrieval_confidence": round(retrieval_confidence, 2),
            "insufficient_evidence": insufficient,
        }

    return node


# ═══════════════════════════════════════════════
# SYNTHESIS NODE (ENHANCED — LANGUAGE-AWARE)
# ═══════════════════════════════════════════════
def synthesis_node(llm):
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        insufficient = state.get("insufficient_evidence", False)
        retrieved_docs = state.get("retrieved_docs", {})
        language = state.get("language", "en")

        context, source_labels = _build_context_with_citations(retrieved_docs)

        if not context.strip():
            from src.utils.translator import get_ui_string
            return {
                "context": "",
                "context_sources": [],
                "response": get_ui_string("insufficient_evidence", language),
                "citations": [],
                "citation_cards": [],
                "citation_valid": False,
                "confidence_score": 0.0,
                "insufficient_evidence": True,
            }

        # Get language-specific instructions
        lang_instructions = LANGUAGE_INSTRUCTIONS.get(language, "")

        query_for_synthesis = state.get("translated_query", state.get("query", ""))
        prompt = SYNTHESIS_PROMPT.format(
            context=context,
            query=query_for_synthesis,
            language_instructions=lang_instructions,
        )

        try:
            response = llm.invoke(prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            from src.utils.translator import get_ui_string
            return {
                "context": context,
                "context_sources": source_labels,
                "response": get_ui_string("error_generating", language),
                "citations": [],
                "citation_cards": [],
                "citation_valid": False,
                "confidence_score": 0.0,
                "insufficient_evidence": True,
            }

        citations = extract_citations(response_text)
        citation_cards = format_citation_cards(citations)

        logger.info(
            f"Synthesis complete: {len(citations)} citations, "
            f"language: {language}"
        )

        return {
            "context": context,
            "context_sources": source_labels,
            "response": response_text,
            "citations": [c["raw"] for c in citations],
            "citation_cards": citation_cards,
            "citation_valid": len(citations) > 0,
            "confidence_score": 0.5,  # Will be overwritten by enforce_citations/verification
        }

    return node


# ═══════════════════════════════════════════════
# VERIFICATION NODE
# ═══════════════════════════════════════════════
def verification_node():
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        response = state.get("response", "")
        context = state.get("context", "")
        # Reuse citations already extracted in synthesis_node
        citation_raws = state.get("citations", [])
        citations_raw = [{"raw": r, "source": "unknown"} for r in citation_raws]

        is_grounded, unsupported, grounding_confidence = verify_answer_grounding(
            response, context, citations_raw
        )

        safety_flags = check_islamic_safety(response, citations_raw)

        source_types = list(set(c.get("source", "unknown") for c in citations_raw))
        if not source_types and is_grounded:
            source_types = ["retrieved_context"]
        elif not source_types:
            source_types = ["none"]

        retrieval_confidence = state.get("retrieval_confidence", 0.5)
        synthesis_confidence = state.get("confidence_score", 0.5)
        final_confidence = (
            retrieval_confidence * 0.3 +
            synthesis_confidence * 0.4 +
            (1.0 if is_grounded else 0.0) * 0.3
        )

        logger.info(
            f"Verification: grounded={is_grounded}, "
            f"confidence={final_confidence:.2f}, "
            f"flags={safety_flags}"
        )

        return {
            "verification_passed": is_grounded,
            "unsupported_claims": unsupported,
            "confidence_score": round(final_confidence, 2),
            "safety_flags": safety_flags,
            "source_types": source_types,
        }

    return node


# ═══════════════════════════════════════════════
# FACT-CHECK NODE — Cross-references citations against context
# ═══════════════════════════════════════════════
def fact_check_node():
    """
    Cross-references every citation in the response against the actual
    retrieved context. Flags hallucinated citations.
    """
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        response = state.get("response", "")
        context = state.get("context", "")
        # Reuse citations already extracted in synthesis_node
        citation_raws = state.get("citations", [])
        citations = [{"raw": r, "source": "unknown"} for r in citation_raws]

        verdicts, hallucination_ratio, fact_check_passed = cross_reference_citations(
            response, context, citations
        )

        logger.info(
            f"Fact-check: {len(verdicts)} citations checked, "
            f"hallucination_ratio={hallucination_ratio}, "
            f"passed={fact_check_passed}"
        )

        # If more than 50% of citations are hallucinated, prepend a warning
        updated_response = response
        if not fact_check_passed:
            updated_response = (
                "⚠️ **Note:** Some citations in this answer could not be "
                "verified against the retrieved sources. Please verify "
                "independently or consult a qualified scholar.\n\n" + response
            )
            logger.warning(
                f"High hallucination ratio ({hallucination_ratio}): "
                f"citations may be fabricated"
            )

        return {
            "citation_verdicts": verdicts,
            "hallucination_ratio": hallucination_ratio,
            "fact_check_passed": fact_check_passed,
            "response": updated_response,
        }

    return node


# ═══════════════════════════════════════════════
# FOLLOW-UP SUGGESTIONS NODE
# ═══════════════════════════════════════════════
def suggest_followups_node(llm):
    """
    Generates 3 relevant follow-up questions based on the Q&A.
    Gracefully degrades to empty list on any failure.
    NOTE: This node is skipped by default to reduce latency.
    It runs only if state["include_followups"] is True.
    """
    FOLLOWUP_PROMPT = """\
Based on the following Islamic Q&A, suggest 3 natural follow-up questions a user might ask.
Make them specific, concise, and related to the topic. Output ONLY a JSON array of strings.

Question: {query}
Answer: {response}

Follow-up questions (JSON array):
"""

    def node(state: IslamicAgentState) -> Dict[str, Any]:
        # Skip follow-up generation by default to reduce latency
        if not state.get("include_followups", False):
            return {"follow_up_questions": []}

        response = state.get("response", "")
        query = state.get("query", "")

        if not response.strip() or not query.strip():
            return {"follow_up_questions": []}

        try:
            prompt = FOLLOWUP_PROMPT.format(
                query=query[:300],
                response=response[:500],
            )
            raw = llm.invoke(prompt)
            raw_text = raw.content if hasattr(raw, "content") else str(raw)

            # Parse JSON array from response
            array_match = re.search(r"\[.*?\]", raw_text, re.DOTALL)
            if array_match:
                questions = json.loads(array_match.group(0))
                if isinstance(questions, list):
                    questions = [
                        str(q).strip()
                        for q in questions[:3]
                        if str(q).strip()
                    ]
                    return {"follow_up_questions": questions}

            logger.warning("Follow-up questions: could not parse JSON array")
            return {"follow_up_questions": []}

        except json.JSONDecodeError as e:
            logger.warning(f"Follow-up questions JSON parse failed: {e}")
            return {"follow_up_questions": []}
        except Exception as e:
            logger.warning(f"Follow-up generation failed: {e}")
            return {"follow_up_questions": []}

    return node


# ═══════════════════════════════════════════════
# RESPONSE FINALIZATION NODE (LANGUAGE-AWARE)
# ═══════════════════════════════════════════════
def finalization_node():
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        from src.utils.translator import get_ui_string

        response = state.get("response", "")
        verification_passed = state.get("verification_passed", False)
        safety_flags = state.get("safety_flags", [])
        confidence = state.get("confidence_score", 0.0)
        insufficient = state.get("insufficient_evidence", False)
        citations = state.get("citations", [])
        language = state.get("language", "en")

        if insufficient and not citations:
            response = get_ui_string("insufficient_evidence", language)
            confidence = 0.0

        elif "sensitive_topic" in safety_flags and "scholarly_opinion" not in state.get("source_types", []):
            response += get_ui_string("scholar_disclaimer", language)

        # Build verse triplets for Quran citations (Arabic/English/Urdu display)
        context = state.get("context", "")
        citation_raws = state.get("citations", [])
        all_citations = [{"raw": r, "source": "quran"} for r in citation_raws]
        verse_triplets = build_verse_triplets(all_citations, context)

        return {
            "response": response,
            "confidence_score": confidence,
            "verse_triplets": verse_triplets,
        }

    return node


# ═══════════════════════════════════════════════
# BUILD GRAPH — 11-STEP PIPELINE
# ═══════════════════════════════════════════════
# Pipeline:
#   classifier → translate_query → retriever → synthesis → verify
#   → fact_check → enforce_citations → finalize → suggest_followups*
#   → translate_response → END
#   (* = skipped by default for latency)
# ═══════════════════════════════════════════════
def build_islamic_graph(vector_store: IslamicVectorStore):
    try:
        llm = _get_llm()
    except RuntimeError:
        logger.warning("No LLM available -- API will use fallback mode")
        raise

    graph = StateGraph(IslamicAgentState)

    # Nodes — 11-step pipeline
    graph.add_node("classifier", lambda state: classifier_node(state, llm))
    graph.add_node("translate_query", translate_query_node(llm))
    graph.add_node("retriever", unified_retriever_node(vector_store))
    graph.add_node("synthesis", synthesis_node(llm))
    graph.add_node("verify", verification_node())
    graph.add_node("fact_check", fact_check_node())
    graph.add_node("enforce_citations", lambda state: enforce_citations(state, llm))
    graph.add_node("finalize", finalization_node())
    graph.add_node("suggest_followups", suggest_followups_node(llm))
    graph.add_node("translate_response", translate_response_node(llm))

    # Flow
    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "translate_query")
    graph.add_edge("translate_query", "retriever")
    graph.add_edge("retriever", "synthesis")
    graph.add_edge("synthesis", "verify")
    graph.add_edge("verify", "fact_check")
    graph.add_edge("fact_check", "enforce_citations")
    graph.add_edge("enforce_citations", "finalize")
    graph.add_edge("finalize", "suggest_followups")
    graph.add_edge("suggest_followups", "translate_response")
    graph.add_edge("translate_response", END)

    return graph.compile()
