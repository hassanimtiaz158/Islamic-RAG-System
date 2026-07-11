# scripts/load_fiqh.py
"""
Loaders for the `fiqh` and `seerah` collections.

These collections are declared in IslamicVectorStore.COLLECTIONS and are
routable by the classifier, but previously had no data loader, so any query
routed to them returned nothing. This module ingests the bundled PDFs/TXT
under data/fiqh and data/seerah (when present).

PDF text is extracted with PyMuPDF (fitz); plain .txt files are read directly.
Chunks are produced with the shared Islamic splitter so metadata is preserved.
"""

from pathlib import Path

from langchain_core.documents import Document

PROJECT_ROOT = Path(__file__).resolve().parent.parent

COLLECTION_DIRS = {
    "fiqh": PROJECT_ROOT / "data" / "fiqh",
    "seerah": PROJECT_ROOT / "data" / "seerah",
}


def _extract_pdf_text(path: Path) -> str:
    import fitz  # PyMuPDF

    text_parts = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n\n".join(t for t in text_parts if t.strip())


def load_islamic_pdfs(collection_key: str) -> list[Document]:
    """
    Load a collection (fiqh/seerah) from bundled PDFs and TXT files.

    Returns an empty list (with a warning) if the data directory is missing,
    so indexing never crashes when a collection has no bundled data.
    """
    data_dir = COLLECTION_DIRS.get(collection_key)
    if data_dir is None or not data_dir.exists():
        print(f"[SKIP] No data directory for '{collection_key}' at {data_dir}")
        return []

    from src.core.islamic_chunker import (
        get_tafsir_splitter,
        split_with_metadata,
    )

    raw_docs: list[Document] = []
    files = sorted(
        [p for p in data_dir.rglob("*") if p.suffix.lower() in (".pdf", ".txt")]
    )

    if not files:
        print(f"[SKIP] No PDF/TXT files found for '{collection_key}' in {data_dir}")
        return []

    print(f"\n[LOAD] Reading {len(files)} file(s) for '{collection_key}'...")
    for path in files:
        try:
            if path.suffix.lower() == ".pdf":
                text = _extract_pdf_text(path)
            else:
                text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  [WARN] Failed to read {path.name}: {e}")
            continue

        if not text.strip():
            continue

        raw_docs.append(Document(
            page_content=text,
            metadata={
                "source": collection_key,
                "collection": collection_key,
                "file": path.name,
                "citation": f"[{collection_key.capitalize()}: {path.stem}]",
            },
        ))

    if not raw_docs:
        print(f"[SKIP] No extractable text for '{collection_key}'")
        return []

    splitter = get_tafsir_splitter()
    chunks = split_with_metadata(raw_docs, splitter)
    print(f"[OK] {collection_key}: {len(chunks)} chunks from {len(raw_docs)} file(s)")
    return chunks


def load_fiqh() -> list[Document]:
    return load_islamic_pdfs("fiqh")


def load_seerah() -> list[Document]:
    return load_islamic_pdfs("seerah")
