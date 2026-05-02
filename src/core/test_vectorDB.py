from langchain_core.documents import Document
from islamic_vectorDB import IslamicVectorStore


def main():
    vector_store = IslamicVectorStore()

    print("✅ Vector store initialized successfully!")

    docs = [
        Document(
            page_content="Indeed, Allah is with the patient.",
            metadata={
                "source": "Quran",
                "reference": "2:153",
            },
        ),
        Document(
            page_content="Actions are judged by intentions.",
            metadata={
                "source": "Hadith",
                "reference": "Bukhari 1",
            },
        ),
    ]

    vector_store.index_documents("test_collection", docs)
    print("✅ Documents indexed successfully!")

    retriever = vector_store.get_retriever("test_collection", k=2)

    results = retriever.invoke("patience in Islam")

    print("\n🔍 Search Results:")
    print("-" * 50)

    for i, doc in enumerate(results, start=1):
        print(f"\nResult {i}")
        print(f"Content  : {doc.page_content}")
        print(f"Metadata : {doc.metadata}")


if __name__ == "__main__":
    main()
