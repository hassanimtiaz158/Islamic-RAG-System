# test_chunker.py

from langchain_core.documents import Document

from islamic_chunker import (
    get_hadith_splitter,
    get_quran_splitter,
    get_tafsir_splitter,
    split_with_metadata,
)


def test_quran_splitter():
    print("\n" + "=" * 60)
    print("Testing Quran Splitter")
    print("=" * 60)

    docs = [
        Document(
            page_content=(
                "Indeed, Allah is with the patient."
            ),
            metadata={
                "source": "Quran",
                "reference": "2:153",
                "citation": "Surah Al-Baqarah 2:153",
            },
        )
    ]

    result = split_with_metadata(docs, get_quran_splitter())

    print(f"Original Documents : {len(docs)}")
    print(f"Split Documents    : {len(result)}")

    assert len(result) == 1
    print("✅ Quran splitter works correctly!")


def test_hadith_splitter():
    print("\n" + "=" * 60)
    print("Testing Hadith Splitter")
    print("=" * 60)

    long_hadith = "Actions are judged by intentions. " * 50

    docs = [
        Document(
            page_content=long_hadith,
            metadata={
                "source": "Bukhari",
                "reference": "Hadith 1",
                "citation": "Sahih Bukhari 1",
            },
        )
    ]

    result = split_with_metadata(docs, get_hadith_splitter())

    print(f"Original Length : {len(long_hadith)} characters")
    print(f"Total Chunks    : {len(result)}")

    for i, chunk in enumerate(result, 1):
        print(f"\nChunk {i}")
        print(f"Length    : {len(chunk.page_content)}")
        print(f"Citation  : {chunk.metadata['citation']}")

    assert len(result) > 1
    print("✅ Hadith splitter works correctly!")


def test_tafsir_splitter():
    print("\n" + "=" * 60)
    print("Testing Tafsir Splitter")
    print("=" * 60)

    long_tafsir = (
        "This verse explains patience and perseverance.\n\n"
        * 80
    )

    docs = [
        Document(
            page_content=long_tafsir,
            metadata={
                "source": "Ibn Kathir",
                "reference": "2:153",
                "citation": "Tafsir Ibn Kathir 2:153",
            },
        )
    ]

    result = split_with_metadata(docs, get_tafsir_splitter())

    print(f"Original Length : {len(long_tafsir)} characters")
    print(f"Total Chunks    : {len(result)}")

    for i, chunk in enumerate(result, 1):
        print(f"\nChunk {i}")
        print(f"Length    : {len(chunk.page_content)}")
        print(f"Citation  : {chunk.metadata['citation']}")

    assert len(result) > 1
    print("✅ Tafsir splitter works correctly!")


if __name__ == "__main__":
    test_quran_splitter()
    test_hadith_splitter()
    test_tafsir_splitter()

    print("\n" + "=" * 60)
    print("🎉 All tests passed successfully!")
    print("=" * 60)
