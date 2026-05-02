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
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
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
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
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
    """
    if splitter is None:
        return documents

    chunks: List[Document] = []

    for document in documents:
        split_docs = splitter.split_documents([document])

        for chunk in split_docs:
            # Preserve all original metadata
            chunk.metadata.update(document.metadata)

            # Ensure citation always exists
            chunk.metadata["citation"] = document.metadata.get(
                "citation",
                "Unknown Source",
            )

            chunks.append(chunk)

    return chunks
