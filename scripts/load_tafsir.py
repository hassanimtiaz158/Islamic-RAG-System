# scripts/load_tafsir.py

import json
from pathlib import Path
from langchain_core.documents import Document


def load_tafsir_from_json(file_path: str | Path) -> list[Document]:
    """
    Load Tafsir JSON and convert into LangChain Documents.
    """

    file_path = Path(r"D:\islamic-rag-system\data\tafsir\tafsir_ibn_kathir.json")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []

    for item in data:
        text = (item.get("tafsir_text") or "").strip()

        if not text:
            continue

        surah = item.get("surah")
        ayah = item.get("ayah")
        source = item.get("tafsir_source", "Unknown Tafsir")
        reference = item.get("reference", f"{surah}:{ayah}")

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": "tafsir",
                    "tafsir_source": source,
                    "surah_number": surah,
                    "ayah_number": ayah,
                    "reference": reference,
                    "citation": f"[{source} {reference}]",
                },
            )
        )

    print(f"Loaded {len(documents)} Tafsir documents successfully.")

    return documents
