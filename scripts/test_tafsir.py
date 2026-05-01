from load_tafsir import load_tafsir_from_json

docs = load_tafsir_from_json("data/tafsir/tafsir_ibn_kathir.json")

print("Total:", len(docs))

print("\nFirst document:")
print(docs[0].page_content[:300])

print("\nMetadata:")
print(docs[0].metadata)
