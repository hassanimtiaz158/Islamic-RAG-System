# scripts/test_islamic_graph.py
import sys
from pathlib import Path

# ----------------------------
# FIX: Add project root
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from islamic_graph import build_islamic_graph
from state import IslamicAgentState


# -----------------------------
# MOCK LLM (for safe testing)
# -----------------------------
class MockLLM:
    def invoke(self, prompt: str):

        # Fake classifier response
        if "classifier" in prompt.lower():
            return """
            {
                "sources": ["quran", "hadith_bukhari"],
                "type": "fiqh"
            }
            """

        # Fake final answer
        return """
        Patience is highly emphasized in Islam.

        Allah says He is with those who are patient. [Quran 2:153]

        The Prophet (PBUH) said actions are based on intention. [Bukhari 1]
        """


# -----------------------------
# MAIN TEST
# -----------------------------
def main():

    print("\n" + "=" * 70)
    print("🧪 TESTING FULL ISLAMIC LANGGRAPH PIPELINE")
    print("=" * 70)

    # Initialize vector store (must already be indexed)
    from core.islamic_vectorDB import IslamicVectorStore

    vector_store = IslamicVectorStore()

    # Build graph
    graph = build_islamic_graph(vector_store)

    # Test input state
    initial_state: IslamicAgentState = {
        "query": "What does Islam say about patience?",
        "query_type": "",
        "retrieved_docs": {},
        "context": "",
        "response": "",
        "citations": [],
        "citation_valid": False,
        "language": "en",
        "iteration": 0,
    }

    print("\n🔍 Input Query:")
    print(initial_state["query"])

    # Run graph
    result = graph.invoke(initial_state)

    print("\n📦 FINAL OUTPUT:")
    print("-" * 50)
    print(result["response"])

    print("\n📚 Retrieved Docs Keys:")
    print(list(result.get("retrieved_docs", {}).keys()))

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
