# src/agents/islamic_graph.py

from langgraph.graph import StateGraph, END
from langchain_ollama import OllamaLLM

#from state import IslamicAgentState
from src.agents.state import IslamicAgentState

from src.core.islamic_vectorDB import EMBED_LOCK, IslamicVectorStore
from src.agents.classifier import classifier_node


SYNTHESIS_PROMPT = """
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
# UNIFIED RETRIEVER NODE (FIXED)
# --------------------------
def unified_retriever_node(vector_store):
    def node(state):

        results = {}

    # 🔒 FULL LOCK (not partial)
        with EMBED_LOCK:

            routing = state.get("routing", ["quran", "hadith_bukhari"])

            for col in routing:

                retriever = vector_store.get_retriever(col, k=4)
                docs = retriever.invoke(state["query"])

                results[col] = [
                {
                    "text": d.page_content,
                    "citation": d.metadata.get("citation", ""),
                }
                for d in docs
            ]

        return {"retrieved_docs": results}


    return node


# --------------------------
# SYNTHESIS NODE
# --------------------------
def synthesis_node(llm):
    def node(state: IslamicAgentState):

        context_blocks = []
        all_citations = []

        # --------------------------
        # Build context + collect citations
        # --------------------------
        for col, docs in state.get("retrieved_docs", {}).items():
            for doc in docs:

                context_blocks.append(
                    f"[{col.upper()}]\n"
                    f"{doc['text']}\n"
                    f"Citation: {doc.get('citation', '')}\n"
                )

                # collect clean citations (IMPORTANT FIX)
                if doc.get("citation"):
                    all_citations.append(doc["citation"])

        context = "\n".join(context_blocks)

        # --------------------------
        # Prompt
        # --------------------------
        prompt = SYNTHESIS_PROMPT.format(
            context=context,
            query=state["query"],
        )

        response = llm.invoke(prompt)
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        # --------------------------
        # FINAL OUTPUT (FIXED)
        # --------------------------
        return {
            "response": response_text,
            "citations": all_citations,
            "citation_valid": len(all_citations) > 0,
        }

    return node



# --------------------------
# BUILD GRAPH
# --------------------------
def build_islamic_graph(vector_store: IslamicVectorStore):

    llm = OllamaLLM(model="phi3", temperature=0.05)

    graph = StateGraph(IslamicAgentState)

    # 1. Nodes
    graph.add_node("classifier", lambda state: classifier_node(state, llm))
    graph.add_node("retriever", unified_retriever_node(vector_store))
    graph.add_node("synthesis", synthesis_node(llm))

    # 2. Flow
    graph.set_entry_point("classifier")

    graph.add_edge("classifier", "retriever")
    graph.add_edge("retriever", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()
