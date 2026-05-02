# scripts/index_all.py

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.islamic_vectorDB import IslamicVectorStore
from src.core.islamic_chunker import (
    get_hadith_splitter,
    split_with_metadata,
)
from scripts.load_quran import load_quran_from_api
from scripts.load_hadiths import load_hadith_collection


HADITH_BOOKS = [
    "bukhari",
    "muslim",
    "abudawud",
    "tirmidhi",
    "nasai",
    "ibnmajah",
]


def index_quran(vector_store: IslamicVectorStore) -> None:
    """Index the Holy Quran."""
    print("\n" + "=" * 70)
    print("📖 Indexing Quran...")
    print("=" * 70)

    quran_docs = load_quran_from_api()
    vector_store.index_documents("quran", quran_docs)

    print("✅ Quran indexed successfully!")


def index_hadith(vector_store: IslamicVectorStore) -> None:
    """Index all six authentic Hadith collections."""
    splitter = get_hadith_splitter()

    for book in HADITH_BOOKS:
        print("\n" + "=" * 70)
        print(f"📚 Indexing {book.title()}...")
        print("=" * 70)

        documents = load_hadith_collection(book)
        chunks = split_with_metadata(documents, splitter)

        collection_name = f"hadith_{book}"
        vector_store.index_documents(collection_name, chunks)

        print(f"✅ {book.title()} indexed successfully!")


def main() -> None:
    """Run complete indexing pipeline."""
    print("\n🚀 Starting Islamic RAG Indexing Pipeline...\n")

    vector_store = IslamicVectorStore()

    index_quran(vector_store)
    index_hadith(vector_store)

    print("\n" + "=" * 70)
    print("🎉 All collections indexed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
