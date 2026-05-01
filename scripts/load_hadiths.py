# scripts/load_hadith.py

import requests
from langchain_core.documents import Document

API_KEY = "$2y$10$EaW8I9L0kEbsv7ubW0tPZIwulE6KhbLMCEHFM4J6tOCp9X6"

HADITH_COLLECTIONS = {
    "bukhari": "sahih-bukhari",
    "muslim": "sahih-muslim",
    "abudawud": "abu-dawud",
    "tirmidhi": "al-tirmidhi",
    "nasai": "sunan-an-nasai",
    "ibnmajah": "ibn-e-majah",
}


def load_hadith_collection(collection_key: str) -> list[Document]:
    """
    Load a Hadith collection from HadithAPI.com.

    Args:
        collection_key: Collection key
            (bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah)

    Returns:
        List of LangChain Document objects
    """

    if collection_key not in HADITH_COLLECTIONS:
        raise ValueError(
            f"Invalid collection '{collection_key}'. "
            f"Available: {list(HADITH_COLLECTIONS.keys())}"
        )

    base_url = "https://hadithapi.com/api/hadiths"
    documents = []
    page = 1

    print(f"Loading {collection_key.title()} hadith collection...\n")

    while True:
        params = {
            "apiKey": API_KEY,
            "book": HADITH_COLLECTIONS[collection_key],
            "paginate": 50,
            "page": page,
        }

        try:
            response = requests.get(
                base_url,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

        except requests.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            break

        hadith_data = data.get("hadiths", {}).get("data", [])

        if not hadith_data:
            break

        for hadith in hadith_data:
            # Some records may contain null values
            text = (hadith.get("hadithEnglish") or "").strip()

            if not text:
                continue

            hadith_number = hadith.get("hadithNumber", "Unknown")
            chapter = (hadith.get("chapterTitle") or "Unknown Chapter").strip()
            grade = (hadith.get("status") or "").strip()
            narrator = (hadith.get("headingEnglish") or "").strip()

            citation = f"[{collection_key.capitalize()} {hadith_number}"

            if grade:
                citation += f" ({grade})"

            citation += "]"

            document = Document(
                page_content=text,
                metadata={
                    "source": "hadith",
                    "collection": collection_key,
                    "book": HADITH_COLLECTIONS[collection_key],
                    "chapter": chapter,
                    "hadith_number": hadith_number,
                    "grade": grade,
                    "narrator": narrator,
                    "citation": citation,
                    "full_ref": (
                        f"{collection_key.capitalize()} "
                        f"Hadith {hadith_number}"
                    ),
                },
            )

            documents.append(document)

        last_page = data.get("hadiths", {}).get("last_page", page)

        print(
            f"Loaded page {page}/{last_page} "
            f"({len(documents)} hadiths so far)"
        )

        if page >= last_page:
            break

        page += 1

    print(
        f"\nSuccessfully loaded "
        f"{len(documents)} hadiths "
        f"from {collection_key.title()}."
    )

    return documents
