# src/agents/test_classifier.py

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.classifier import classifier_node
from src.agents.state import IslamicAgentState


class MockLLM:
    """Fake LLM for testing without API calls."""

    def invoke(self, prompt: str):
        return """
        {
            "sources": ["quran", "hadith_bukhari"],
            "type": "fiqh"
        }
        """


def main():
    print("\n" + "=" * 60)
    print("🧪 Testing Islamic Classifier Node")
    print("=" * 60)

    state: IslamicAgentState = {
        "query": "Is interest in Islam halal or haram?",
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

    llm = MockLLM()
    result = classifier_node(state, llm)

    print("\n🔍 Input Query:")
    print(state["query"])
    print("\n📦 Output:")
    print(result)

    assert "query_type" in result
    assert "routing" in result
    assert isinstance(result["routing"], list)

    print("\n✅ Classifier working correctly!")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
