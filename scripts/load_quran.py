# scripts/load_quran.py

from chromadb import Documents
import requests
from langchain_core.documents import Document


def load_quran_from_api() -> list[Document]:
    """
    Load full Quran (English translation) from AlQuran.cloud API
    Returns: List of LangChain Document objects
    """

    # API for Yusuf Ali English translation
    url = "https://api.alquran.cloud/v1/quran/en.yusufali"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()["data"]

        documents = []

        for surah in data["surahs"]:
            surah_num = surah["number"]
            surah_name = surah["englishName"]
            surah_arabic = surah["name"]

            for ayah in surah["ayahs"]:
                ayah_num = ayah["numberInSurah"]
                text = ayah["text"]

                doc = Document(
                    page_content=text,
                    metadata={
                        "source": "quran",
                        "surah_number": surah_num,
                        "surah_name": surah_name,
                        "surah_arabic": surah_arabic,
                        "ayah_number": ayah_num,
                        "citation": f"[Quran {surah_name} {surah_num}:{ayah_num}]",
                        "full_ref": f"Surah {surah_name} ({surah_num}), Ayah {ayah_num}",
                    },
                )

                documents.append(doc)

        print(f"Loaded {len(documents)} Ayahs from Quran successfully.")
        return documents

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Quran data: {e}")
        return []
    
