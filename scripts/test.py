# test_loader.py

from load_quran import load_quran_from_api
from load_hadiths import load_hadith_collection


def test_quran_loader():
    print("=" * 60)
    print("Testing Quran Loader")
    print("=" * 60)

    quran_docs = load_quran_from_api()

    print(f"Total Ayahs Loaded: {len(quran_docs)}")

    if quran_docs:
        first_doc = quran_docs[0]

        print("\nFirst Ayah:")
        print(first_doc.page_content)

        print("\nMetadata:")
        for key, value in first_doc.metadata.items():
            print(f"{key}: {value}")


def test_hadith_loader():
    print("\n" + "=" * 60)
    print("Testing Hadith Loader")
    print("=" * 60)

    hadith_docs = load_hadith_collection("bukhari")

    print(f"Total Hadith Loaded: {len(hadith_docs)}")

    if hadith_docs:
        first_doc = hadith_docs[0]

        print("\nFirst Hadith:")
        print(first_doc.page_content[:500] + "...")

        print("\nMetadata:")
        for key, value in first_doc.metadata.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    test_quran_loader()
    test_hadith_loader()
