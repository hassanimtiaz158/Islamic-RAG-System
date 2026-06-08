# src/agents/final_test_query.py

import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.islamic_vectorDB import IslamicVectorStore
from src.agents.islamic_graph import build_islamic_graph
from src.agents.state import IslamicAgentState


def main():
    print("\n" + "=" * 70)
    print("🧪 FULL LANGGRAPH ISLAMIC RAG TEST")
    print("=" * 70)

    vector_store = IslamicVectorStore()
    graph = build_islamic_graph(vector_store)

    query = "What is the Islamic ruling on fasting on Mondays and Thursdays?"

    state: IslamicAgentState = {
        "query": query,
        "query_type": "",
        "retrieved_docs": {},
        "context": "",
        "response": "",
        "citations": [],
        "citation_cards": [],
        "citation_valid": False,
        "language": "en",
        "iteration": 0,
    }

    print("\n🔍 Query:")
    print(query)

    result = graph.invoke(state)

    print("\n📌 FINAL ANSWER:")
    print("-" * 50)
    print(result["response"])

    print("\n📚 Retrieved Sources:")
    print(result.get("retrieved_docs", {}).keys())

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
