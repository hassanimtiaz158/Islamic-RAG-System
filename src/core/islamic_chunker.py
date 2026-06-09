# src/core/islamic_chunker.py

from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def get_quran_splitter() -> None:
    """
    Quran verses are already atomic units.
    Each ayah should remain a separate document.
    """
    return None


def get_hadith_splitter() -> RecursiveCharacterTextSplitter:
    """
    Split lengthy hadith into smaller semantic chunks.
    Hadith are typically short, so we use conservative chunking.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
        ],
        keep_separator=True,
    )


def get_tafsir_splitter() -> RecursiveCharacterTextSplitter:
    """
    Split tafsir at paragraph boundaries while preserving context.
    Tafsir entries can be lengthy, so we allow larger chunks.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
        ],
        keep_separator=True,
    )


def split_with_metadata(
    documents: List[Document],
    splitter: Optional[RecursiveCharacterTextSplitter],
) -> List[Document]:
    """
    Split documents while preserving parent metadata.
    Each chunk inherits all metadata from its parent document.
    """
    if splitter is None:
        return documents

    chunks: List[Document] = []

    for document in documents:
        split_docs = splitter.split_documents([document])

        for i, chunk in enumerate(split_docs):
            # Preserve all original metadata
            chunk.metadata.update(document.metadata)

            # Ensure citation always exists
            chunk.metadata["citation"] = document.metadata.get(
                "citation",
                "Unknown Source",
            )

            # Add chunk index for traceability
            chunk.metadata["chunk_index"] = i
            chunk.metadata["total_chunks"] = len(split_docs)

            chunks.append(chunk)

    return chunks
