# scripts/load_hadiths.py

import os
import time
import requests
from langchain_core.documents import Document

API_KEY = os.getenv("HADITH_API_KEY", "")


def _require_api_key() -> str:
    """Return the Hadith API key, raising only when actually needed."""
    if not API_KEY:
        raise RuntimeError(
            "HADITH_API_KEY environment variable is required. "
            "Get a free key at https://hadithapi.com and set it via:\n"
            "  export HADITH_API_KEY=your_key_here"
        )
    return API_KEY

# Corrected slugs for HadithAPI.com
HADITH_COLLECTIONS = {
    "bukhari": "sahih-bukhari",
    "muslim": "sahih-muslim",
    "abudawud": "sunan-abu-dawud",       # Fixed: was "abu-dawud"
    "tirmidhi": "al-tirmidhi",
    "nasai": "sunan-nasai",               # Fixed: was "sunan-an-nasai"
    "ibnmajah": "ibn-e-majah",
}

# Map internal collection key to citation display name
CITATION_NAMES = {
    "bukhari": "Bukhari",
    "muslim": "Muslim",
    "abudawud": "Abu Dawud",
    "tirmidhi": "Tirmidhi",
    "nasai": "Nasai",
    "ibnmajah": "Ibn Majah",
}


def _fetch_page(url, params, max_retries=3, base_timeout=30):
    """Fetch a page with retry logic and exponential backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            timeout = base_timeout + (attempt - 1) * 15  # Increase timeout each retry
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code == 429:  # Rate limit
                wait = attempt * 5
                print(f"  [RATE LIMIT] Waiting {wait}s before retry {attempt}/{max_retries}...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            wait = attempt * 3
            print(f"  [TIMEOUT] Page {params.get('page', '?')} attempt {attempt}/{max_retries} — retrying in {wait}s...")
            time.sleep(wait)
        except requests.exceptions.ConnectionError:
            wait = attempt * 5
            print(f"  [CONNECTION ERROR] Attempt {attempt}/{max_retries} — retrying in {wait}s...")
            time.sleep(wait)
        except requests.exceptions.HTTPError as e:
            if response.status_code in (500, 502, 503, 504):
                wait = attempt * 4
                print(f"  [SERVER ERROR {response.status_code}] Attempt {attempt}/{max_retries} — retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [HTTP ERROR] {e}")
                raise
    return None  # All retries exhausted


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

    api_key = _require_api_key()
    base_url = "https://hadithapi.com/api/hadiths"
    documents = []
    page = 1
    citation_name = CITATION_NAMES.get(collection_key, collection_key.capitalize())

    print(f"Loading {collection_key.title()} hadith collection (slug: {HADITH_COLLECTIONS[collection_key]})...\n")

    while True:
        params = {
            "apiKey": api_key,
            "book": HADITH_COLLECTIONS[collection_key],
            "paginate": 50,
            "page": page,
        }

        data = _fetch_page(base_url, params, max_retries=3)

        if data is None:
            print(f"  [SKIP] Page {page} failed after all retries — stopping.")
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

            citation = f"[{citation_name} {hadith_number}"

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
                        f"{citation_name} "
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
