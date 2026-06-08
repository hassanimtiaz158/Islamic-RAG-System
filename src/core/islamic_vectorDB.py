# src/core/islamic_vectorstore.py

from pathlib import Path
import threading
EMBED_LOCK = threading.Lock()


import chromadb
from chromadb.config import Settings

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import Chroma


COLLECTIONS = {
    "quran": "All 6,236 Quran ayaat with English translation",
    "hadith_bukhari": "Sahih Bukhari - 7,563 hadiths",
    "hadith_muslim": "Sahih Muslim - 7,563 hadiths",
    "hadith_dawud": "Sunan Abu Dawud - 5,274 hadiths",
    "hadith_tirmidhi": "Jami at-Tirmidhi - 3,956 hadiths",
    "hadith_nasai": "Sunan an-Nasai - 5,761 hadiths",
    "hadith_ibnmajah": "Sunan Ibn Majah - 4,341 hadiths",
    "tafsir": "Tafsir Ibn Kathir - Verse-by-verse commentary",
    "fiqh": "Islamic rulings from IslamQA",
    "seerah": "Biography of Prophet Muhammad (PBUH)",
}


class IslamicVectorStore:
    """
    Centralized vector store manager for all Islamic knowledge collections.
    """

    def __init__(self, persist_directory: str = "data/vectorstore") -> None:
        self.persist_directory = Path(persist_directory)

        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={
                "normalize_embeddings": True,
                "batch_size": 64,
            },
        )

        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        self._stores = {}

    def get_store(self, collection_name: str) -> Chroma:
        """
        Get or create a Chroma collection.
        """
        if collection_name not in self._stores:
            self._stores[collection_name] = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                client=self.client,
            )

        return self._stores[collection_name]

    def index_documents(
        self,
        collection_name: str,
        documents: list,
        batch_size: int = 100,
    ) -> None:
        """
        Index documents into a Chroma collection.
        """
        store = self.get_store(collection_name)

        total_docs = len(documents)

        for i in range(0, total_docs, batch_size):
            batch = documents[i : i + batch_size]
            store.add_documents(batch)

            indexed = min(i + batch_size, total_docs)
            print(
                f"[{collection_name}] Indexed "
                f"{indexed}/{total_docs} documents"
            )

    def safe_embed_query(self, text):
        with EMBED_LOCK:
            return self.embeddings.embed_query(text)

    def get_retriever(self, collection_name: str, k: int = 5):
        """
        Create an MMR retriever for a collection.
        """
        return self.get_store(collection_name).as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,
                "fetch_k": k * 4,
                "lambda_mult": 0.75,
            },
        )

    def list_collections(self) -> list[str]:
        """
        Return all available collections.
        """
        return list(COLLECTIONS.keys())

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection and remove from cache."""
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass
        self._stores.pop(collection_name, None)
