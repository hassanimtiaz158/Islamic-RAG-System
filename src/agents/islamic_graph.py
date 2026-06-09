# src/agents/islamic_graph.py

import os
import json
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from src.agents.state import IslamicAgentState
from src.core.islamic_vectorDB import EMBED_LOCK, IslamicVectorStore
from src.agents.classifier import classifier_node
from src.utils.citation_engine import (
    extract_citations,
    format_citation_cards,
    enforce_citations,
    verify_answer_grounding,
    check_islamic_safety,
)

load_dotenv()
logger = logging.getLogger("islamic-rag")


# ═══════════════════════════════════════════════
# MODEL INITIALIZATION
# ═══════════════════════════════════════════════
def _get_llm():
    """Get an LLM based on environment configuration."""
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model = os.getenv("LLM_MODEL", "phi3")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model or "gpt-4o-mini",
                    temperature=0.0,  # Zero temperature for factual accuracy
                    api_key=api_key,
                )
            except Exception as e:
                logger.warning(f"OpenAI LLM init failed: {e}")

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        if api_key:
            try:
                from langchain_groq import ChatGroq
                return ChatGroq(
                    model=model or "llama-3.1-8b-instant",
                    temperature=0.0,
                    groq_api_key=api_key,
                )
            except ImportError:
                logger.warning("langchain-groq not installed. Run: pip install langchain-groq")
            except Exception as e:
                logger.warning(f"Groq LLM init failed: {e}")

    # Default: try Ollama
    try:
        from langchain_ollama import OllamaLLM
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaLLM(
            model=model or "phi3",
            temperature=0.0,
            base_url=base_url,
        )
    except Exception as e:
        logger.warning(f"Ollama LLM init failed: {e}")
        raise RuntimeError(
            "No working LLM provider configured. "
            "Set LLM_PROVIDER=openai with OPENAI_API_KEY, "
            "LLM_PROVIDER=groq with GROQ_API_KEY, "
            "or ensure Ollama is running."
        )


# ═══════════════════════════════════════════════
# SYNTHESIS PROMPT — ZERO-HALLUCINATION
# ═══════════════════════════════════════════════
SYNTHESIS_PROMPT = """\
You are Al-Ilm, an Islamic knowledge assistant. Your task is to answer questions using ONLY the provided Islamic sources.

═══════════════════════════════════════
CRITICAL RULES — VIOLATION = REJECTION
═══════════════════════════════════════

1. USE ONLY PROVIDED SOURCES
   • Every claim must come from the sources below.
   • NEVER use your own knowledge, even if you "know" the answer.
   • If a fact is not in the sources, do NOT include it.

2. CITATION FORMAT (MANDATORY — PERFECT ACCURACY REQUIRED)
   Each citation MUST match one from the sources below EXACTLY.

   Quran:     [Quran SurahName Chapter:Verse]
              Example: [Quran Al-Baqarah 2:153]

   Hadith:    [Collection Number] or [Collection Chapter, No. Number]
              Examples: [Bukhari 1469]  [Bukhari, Book of Fasting, No. 1985]
                        [Muslim 2999]   [Abu Dawud 45]
                        [Tirmidhi 1089] [Nasai 1234]  [Ibn Majah 567]

   Tafsir:    [Tafsir Source Reference]
              Example: [Tafsir Ibn Kathir 2:153]

3. EVERY SENTENCE WITH A FACTUAL CLAIM MUST END WITH A CITATION.
   • If you cannot cite it, DELETE it.
   • NEVER write "Ayah:2-3" or ranges.
   • NEVER use parentheses inside citations.
   • NEVER modify citation formatting.

4. INSUFFICIENT SOURCES → ADMIT IT
   If the sources do NOT contain information to answer the question:
   → Write: "I could not find sufficient evidence in the available Islamic sources."
   → Do NOT guess, infer, or fabricate.

5. DISTINGUISH SOURCE TYPES
   • For direct Quran quotes: Use [Quran ...] and optionally quote the Arabic
   • For direct Hadith: Use the exact citation from the source
   • For scholarly opinions not directly from sources: Preface with
     "According to scholarly interpretation based on these sources..." and add
     a safety note recommending consultation with a qualified scholar.

6. SAFETY
   • NEVER invent Quran references.
   • NEVER invent Hadith references.
   • NEVER fabricate scholars or books.
   • If sources conflict, present both and note the difference.
   • For sensitive rulings, add: "Please consult a qualified Islamic scholar."

═══════════════════════════════════════
RETRIEVED ISLAMIC SOURCES
═══════════════════════════════════════
{context}

═══════════════════════════════════════
QUESTION
═══════════════════════════════════════
{query}

═══════════════════════════════════════
ANSWER (every factual claim MUST end with a citation from above sources):
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
# UNIFIED RETRIEVER NODE (ENHANCED)
# ═══════════════════════════════════════════════
def unified_retriever_node(vector_store: IslamicVectorStore):
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        results = {}
        all_scores = {}

        routing = state.get("routing", ["quran", "hadith_bukhari"])
        query = state.get("query", "")

        logger.info(f"Retrieving from collections: {routing}")

        with EMBED_LOCK:
            for col in routing:
                try:
                    # Use retrieve_with_scores for threshold filtering
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

        # Check if we have any meaningful results
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
# SYNTHESIS NODE (ENHANCED)
# ═══════════════════════════════════════════════
def synthesis_node(llm):
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        insufficient = state.get("insufficient_evidence", False)
        retrieved_docs = state.get("retrieved_docs", {})

        # Build context
        context, source_labels = _build_context_with_citations(retrieved_docs)

        # If no context was retrieved, return early with safe response
        if not context.strip():
            return {
                "context": "",
                "context_sources": [],
                "response": (
                    "I could not find sufficient evidence in the available Islamic sources "
                    "to answer this question. Please try rephrasing your question or "
                    "selecting additional sources. For specific Islamic rulings, "
                    "please consult a qualified Islamic scholar."
                ),
                "citations": [],
                "citation_cards": [],
                "citation_valid": False,
                "confidence_score": 0.0,
                "insufficient_evidence": True,
            }

        # Generate answer
        prompt = SYNTHESIS_PROMPT.format(
            context=context,
            query=state["query"],
        )

        try:
            response = llm.invoke(prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return {
                "context": context,
                "context_sources": source_labels,
                "response": (
                    "I encountered an error generating the answer. "
                    "Please try again."
                ),
                "citations": [],
                "citation_cards": [],
                "citation_valid": False,
                "confidence_score": 0.0,
                "insufficient_evidence": True,
            }

        # Extract citations
        citations = extract_citations(response_text)
        citation_cards = format_citation_cards(citations)

        # Immediate grounding check (pre-verification)
        is_grounded, unsupported, grounding_confidence = verify_answer_grounding(
            response_text, context, citations
        )

        logger.info(
            f"Synthesis complete: {len(citations)} citations, "
            f"grounded: {is_grounded}, confidence: {grounding_confidence:.2f}"
        )

        return {
            "context": context,
            "context_sources": source_labels,
            "response": response_text,
            "citations": [c["raw"] for c in citations],
            "citation_cards": citation_cards,
            "citation_valid": len(citations) > 0,
            "confidence_score": round(grounding_confidence, 2),
        }

    return node


# ═══════════════════════════════════════════════
# VERIFICATION NODE (NEW)
# ═══════════════════════════════════════════════
def verification_node():
    """
    Dedicated verification step that runs between synthesis and citation enforcement.
    Checks grounding, Islamic safety, and flags issues.
    """
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        response = state.get("response", "")
        context = state.get("context", "")
        citations_raw = extract_citations(response)

        # Run grounding verification
        is_grounded, unsupported, grounding_confidence = verify_answer_grounding(
            response, context, citations_raw
        )

        # Run Islamic safety check
        safety_flags = check_islamic_safety(response, citations_raw)

        # Determine source types
        source_types = list(set(c.get("source", "unknown") for c in citations_raw))
        if not source_types and is_grounded:
            source_types = ["retrieved_context"]
        elif not source_types:
            source_types = ["none"]

        # Combine confidence scores
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
# RESPONSE FINALIZATION NODE (NEW)
# ═══════════════════════════════════════════════
def finalization_node():
    """
    Final node that applies post-verification adjustments:
    - Adds scholarly disclaimers for sensitive topics
    - Overrides response if verification completely failed
    """
    def node(state: IslamicAgentState) -> Dict[str, Any]:
        response = state.get("response", "")
        verification_passed = state.get("verification_passed", False)
        safety_flags = state.get("safety_flags", [])
        confidence = state.get("confidence_score", 0.0)
        insufficient = state.get("insufficient_evidence", False)
        citations = state.get("citations", [])

        # If no evidence at all and no citations, override completely
        if insufficient and not citations:
            response = (
                "I could not find sufficient evidence in the available Islamic sources "
                "to answer this question. Please try rephrasing your question or "
                "selecting additional sources. For specific Islamic rulings, "
                "please consult a qualified Islamic scholar."
            )
            confidence = 0.0

        # Add disclaimer for sensitive topics
        elif "sensitive_topic" in safety_flags and "scholarly_opinion" not in state.get("source_types", []):
            response += (
                "\n\n⚠️ **Important Note:** This topic involves nuanced Islamic rulings. "
                "The information above is based on the retrieved sources. "
                "For personal religious obligations (farāḍ, ḥarām, ḥalāl), "
                "please consult a qualified Islamic scholar who can consider "
                "your specific circumstances."
            )

        return {
            "response": response,
            "confidence_score": confidence,
        }

    return node


# ═══════════════════════════════════════════════
# BUILD GRAPH
# ═══════════════════════════════════════════════
def build_islamic_graph(vector_store: IslamicVectorStore):
    try:
        llm = _get_llm()
    except RuntimeError:
        logger.warning("No LLM available -- graph will use fallback mode")
        llm = None

    graph = StateGraph(IslamicAgentState)

    # Nodes — 7-step pipeline
    graph.add_node("classifier", lambda state: classifier_node(state, llm))
    graph.add_node("retriever", unified_retriever_node(vector_store))
    graph.add_node("synthesis", synthesis_node(llm))
    graph.add_node("verify", verification_node())
    graph.add_node("enforce_citations", lambda state: enforce_citations(state, llm))
    graph.add_node("finalize", finalization_node())

    # Flow
    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "retriever")
    graph.add_edge("retriever", "synthesis")
    graph.add_edge("synthesis", "verify")
    graph.add_edge("verify", "enforce_citations")
    graph.add_edge("enforce_citations", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()
