# src/agents/islamic_graph.py

import os
import json
import logging

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from src.agents.state import IslamicAgentState
from src.core.islamic_vectorDB import EMBED_LOCK, IslamicVectorStore
from src.agents.classifier import classifier_node
from src.utils.citation_engine import extract_citations, format_citation_cards, enforce_citations

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
                    temperature=0.05,
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
                    temperature=0.05,
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
            temperature=0.05,
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


SYNTHESIS_PROMPT = """\
You are a knowledgeable Islamic scholar assistant.

Answer the question using ONLY the provided authentic Islamic sources.

========================
MANDATORY CITATION FORMAT (STRICT — DO NOT BREAK)
========================

QURAN:
[Quran SurahName Chapter:Verse]

Example:
[Quran Al-Baqarah 2:153]

HADITH:
[Bukhari 1302]
[Muslim 89]
[Abu Dawud 45]
[Tirmidhi 210]
[Nasai 1234]
[Ibn Majah 567]

========================
RULES
========================
- NEVER write "Ayah:2-3"
- NEVER write ranges like "2-3"
- NEVER add words inside brackets except required format
- NEVER use parentheses inside citations
- EACH factual claim MUST end with a citation
- If source is not found, say: "I could not find this in the provided sources."
- Do NOT fabricate hadith or Quran verses
- Be concise, accurate, and scholarly

========================
AUTHENTIC SOURCES
========================
{context}

QUESTION:
{query}

ANSWER (with mandatory citations):
"""


# --------------------------
# UNIFIED RETRIEVER NODE
# --------------------------
def unified_retriever_node(vector_store):
    def node(state):
        results = {}

        # 🔒 FULL LOCK (not partial)
        with EMBED_LOCK:
            routing = state.get("routing", ["quran", "hadith_bukhari"])

            for col in routing:
                try:
                    retriever = vector_store.get_retriever(col, k=4)
                    docs = retriever.invoke(state["query"])

                    results[col] = [
                        {
                            "text": d.page_content,
                            "citation": d.metadata.get("citation", ""),
                        }
                        for d in docs
                    ]
                except Exception as e:
                    logger.warning(f"Retrieval failed for {col}: {e}")
                    results[col] = []

        return {"retrieved_docs": results}

    return node


# --------------------------
# SYNTHESIS NODE
# --------------------------
def synthesis_node(llm):
    def node(state: IslamicAgentState):
        context_blocks = []
        all_citations = []

        # Build context + collect citations
        for col, docs in state.get("retrieved_docs", {}).items():
            for doc in docs:
                context_blocks.append(
                    f"[{col.upper()}]\n"
                    f"{doc['text']}\n"
                    f"Citation: {doc.get('citation', '')}\n"
                )

                if doc.get("citation"):
                    all_citations.append(doc["citation"])

        context = "\n".join(context_blocks)

        # If no context was retrieved, return a safe answer
        if not context.strip():
            return {
                "response": "I could not find this in the available Islamic sources. Please try a different question or select additional sources.",
                "citations": [],
                "citation_cards": [],
                "citation_valid": False,
                "context": "",
            }

        prompt = SYNTHESIS_PROMPT.format(
            context=context,
            query=state["query"],
        )

        response = llm.invoke(prompt)
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        # Extract and format citations from the response
        citations = extract_citations(response_text)
        citation_cards = format_citation_cards(citations)

        return {
            "response": response_text,
            "citations": [c["raw"] for c in citations],
            "citation_cards": citation_cards,
            "citation_valid": len(citations) > 0,
            "context": context,
        }

    return node


# --------------------------
# BUILD GRAPH
# --------------------------
def build_islamic_graph(vector_store: IslamicVectorStore):
    try:
        llm = _get_llm()
    except RuntimeError:
        logger.warning("No LLM available — graph will use fallback mode")
        llm = None

    graph = StateGraph(IslamicAgentState)

    # 1. Nodes
    graph.add_node("classifier", lambda state: classifier_node(state, llm))
    graph.add_node("retriever", unified_retriever_node(vector_store))
    graph.add_node("synthesis", synthesis_node(llm))
    graph.add_node("enforce_citations", lambda state: enforce_citations(state, llm))

    # 2. Flow
    graph.set_entry_point("classifier")

    graph.add_edge("classifier", "retriever")
    graph.add_edge("retriever", "synthesis")
    graph.add_edge("synthesis", "enforce_citations")
    graph.add_edge("enforce_citations", END)

    return graph.compile()
