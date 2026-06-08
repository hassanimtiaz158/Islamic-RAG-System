# scripts/index_all.py

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.islamic_vectorDB import IslamicVectorStore
from src.core.islamic_chunker import (
    get_hadith_splitter,
    get_tafsir_splitter,
    split_with_metadata,
)
from scripts.load_quran import load_quran_from_api
from scripts.load_hadiths import load_hadith_collection
from scripts.load_tafsir import load_tafsir_from_json


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
    print("[QURAN] Indexing Quran...")
    print("=" * 70)

    quran_docs = load_quran_from_api()
    vector_store.index_documents("quran", quran_docs)

    print(f"[OK] Quran indexed: {len(quran_docs)} ayahs")


def index_hadith(vector_store: IslamicVectorStore) -> None:
    """Index all six authentic Hadith collections."""
    splitter = get_hadith_splitter()

    for book in HADITH_BOOKS:
        print("\n" + "=" * 70)
        print(f"[HADITH] Indexing {book.title()}...")
        print("=" * 70)

        documents = load_hadith_collection(book)
        chunks = split_with_metadata(documents, splitter)

        collection_name = f"hadith_{book}"
        vector_store.index_documents(collection_name, chunks)

        print(f"[OK] {book.title()} indexed: {len(chunks)} chunks")


def index_tafsir(vector_store: IslamicVectorStore) -> None:
    """Index Tafsir Ibn Kathir."""
    print("\n" + "=" * 70)
    print("[TAFSIR] Indexing Tafsir Ibn Kathir...")
    print("=" * 70)

    tafsir_path = PROJECT_ROOT / "data" / "tafsir" / "tafsir_ibn_kathir.json"
    if not tafsir_path.exists():
        print(f"[SKIP] Tafsir file not found at {tafsir_path}")
        return

    tafsir_docs = load_tafsir_from_json(tafsir_path)
    splitter = get_tafsir_splitter()
    chunks = split_with_metadata(tafsir_docs, splitter)

    vector_store.index_documents("tafsir", chunks)

    print(f"[OK] Tafsir indexed: {len(chunks)} chunks")


def main() -> None:
    """Run complete indexing pipeline."""
    print("\n[START] Starting Islamic RAG Indexing Pipeline...\n")

    vector_store = IslamicVectorStore()

    index_quran(vector_store)
    index_hadith(vector_store)
    index_tafsir(vector_store)

    print("\n" + "=" * 70)
    print("[DONE] All collections indexed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
