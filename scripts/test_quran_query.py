# scripts/test_quran_query.py

import sys
from pathlib import Path

# ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.islamic_vectorDB import IslamicVectorStore


def main():
    vs = IslamicVectorStore()

    query = "what does the Quran say about patience"

    print("\n" + "=" * 60)
    print(f"🔍 Query: {query}")
    print("=" * 60)

    retriever = vs.get_retriever("quran", k=5)

    results = retriever.invoke(query)

    for i, doc in enumerate(results, 1):
        print(f"\nResult {i}")
        print("-" * 40)
        print("Ayah:", doc.page_content)
        print("Metadata:", doc.metadata)

    print("\n" + "=" * 60)
    print("✅ Test completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
