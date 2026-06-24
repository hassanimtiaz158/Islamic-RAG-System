# src/core/islamic_vectorstore.py

import threading
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import chromadb
from chromadb.config import Settings

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

logger = logging.getLogger("islamic-rag.vectorstore")

EMBED_LOCK = threading.Lock()

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

# Minimum relevance score (cosine similarity 0-1) below which results are filtered
MIN_RELEVANCE_THRESHOLD = 0.3


class IslamicVectorStore:
    """
    Centralized vector store manager for all Islamic knowledge collections.
    Features:
    - Thread-safe embedding with EMBED_LOCK
    - MMR retrieval for diverse results
    - Relevance threshold filtering
    - Retrieval confidence scoring
    - Multi-tenant support via tenant_id parameter
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
        """Get or create a Chroma collection."""
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
        """Index documents into a Chroma collection."""
        store = self.get_store(collection_name)
        total_docs = len(documents)

        for i in range(0, total_docs, batch_size):
            batch = documents[i : i + batch_size]
            store.add_documents(batch)
            indexed = min(i + batch_size, total_docs)
            print(f"[{collection_name}] Indexed {indexed}/{total_docs} documents")

    def retrieve_with_scores(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
        tenant_id: Optional[str] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Retrieve documents with relevance scores.
        Returns list of (Document, score) tuples, filtered by threshold.
        tenant_id: optional filter for per-tenant collections.
        """
        # Resolve actual collection name (tenant-scoped if tenant_id provided)
        actual_collection = self._resolve_collection(collection_name, tenant_id)
        store = self.get_store(actual_collection)
        with EMBED_LOCK:
            results = store.similarity_search_with_relevance_scores(
                query, k=k
            )

        # Filter by threshold
        filtered = [
            (doc, score) for doc, score in results
            if score >= MIN_RELEVANCE_THRESHOLD
        ]

        if not filtered and results:
            # If everything is below threshold, take the top result anyway
            # but log a warning
            logger.warning(
                f"All results for '{query[:50]}...' in '{collection_name}' "
                f"below threshold {MIN_RELEVANCE_THRESHOLD}. "
                f"Best score: {results[0][1]:.3f}"
            )
            filtered = [results[0]]

        return filtered

    def compute_retrieval_confidence(
        self,
        all_results: Dict[str, List[Tuple[Document, float]]],
    ) -> float:
        """
        Compute overall retrieval confidence across all collections.
        Based on the number and quality of retrieved results.
        """
        if not all_results:
            return 0.0

        total_docs = 0
        total_score = 0.0

        for collection_name, results in all_results.items():
            for doc, score in results:
                total_docs += 1
                total_score += score

        if total_docs == 0:
            return 0.0

        avg_score = total_score / total_docs

        # Factor in the number of documents retrieved
        # More relevant documents = higher confidence
        count_factor = min(total_docs / 4.0, 1.0)  # Cap at 4 docs

        confidence = avg_score * 0.7 + count_factor * 0.3
        return min(max(confidence, 0.0), 1.0)

    def list_collections(self) -> list[str]:
        """Return all available collections."""
        return list(COLLECTIONS.keys())

    def get_collection_count(self, collection_name: str) -> int:
        """Get the number of documents in a collection."""
        try:
            col = self.client.get_collection(collection_name)
            return col.count()
        except Exception:
            return 0

    def _resolve_collection(self, collection_name: str, tenant_id: Optional[str] = None) -> str:
        """Resolve collection name, applying tenant scoping if needed.

        Shared collections (quran, hadith_*, tafsir, fiqh, seerah) are global.
        User uploads and custom collections are tenant-scoped.
        """
        shared_collections = {"quran", "hadith_bukhari", "hadith_muslim", "hadith_dawud",
                              "hadith_tirmidhi", "hadith_nasai", "hadith_ibnmajah",
                              "tafsir", "fiqh", "seerah"}

        if collection_name in shared_collections or tenant_id is None:
            return collection_name

        return f"tenant_{tenant_id}_{collection_name}"

