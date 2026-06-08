"""Run indexing pipeline with a fresh vectorstore directory."""
import sys, os, shutil, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Use a fresh directory to avoid lock issues on Windows
# Use a unique fresh directory each run to avoid Windows file lock issues
import uuid
fresh_dir = f'data/vectorstore_{uuid.uuid4().hex[:8]}'
print(f'Using fresh directory: {fresh_dir}')
os.makedirs(fresh_dir, exist_ok=True)

t0 = time.time()

print("=" * 60)
print("STARTING INDEXING PIPELINE")
print("=" * 60)

from src.core.islamic_vectorDB import IslamicVectorStore
from src.core.islamic_chunker import get_hadith_splitter, split_with_metadata
from scripts.load_quran import load_quran_from_api
from scripts.load_hadiths import load_hadith_collection

# Init with fresh directory
print("\nInitializing vector store...")
vs = IslamicVectorStore(persist_directory=fresh_dir)
print("Vector store ready!")

# Step 1: Index Quran
print("\n--- Loading Quran ---")
quran_docs = load_quran_from_api()
print(f"Loaded {len(quran_docs)} ayahs")
print("Indexing Quran...")
vs.index_documents("quran", quran_docs)
print("Quran indexing complete!")

# Step 2: Index Hadith collections (start with bukhari, then the rest)
HADITH_BOOKS = ["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah"]
splitter = get_hadith_splitter()

for book in HADITH_BOOKS:
    print(f"\n--- Loading {book.title()} ---")
    try:
        docs = load_hadith_collection(book)
        print(f"Loaded {len(docs)} hadiths")
        chunks = split_with_metadata(docs, splitter)
        print(f"Split into {len(chunks)} chunks")
        vs.index_documents(f"hadith_{book}", chunks)
        print(f"{book.title()} indexing complete!")
    except Exception as e:
        print(f"ERROR indexing {book}: {e}")

elapsed = time.time() - t0
print(f"\n{'=' * 60}")
print(f"ALL DONE! Total time: {elapsed:.1f} seconds")
print(f"{'=' * 60}")

# Print summary of collections
print("\nIndexed collections:")
for c in vs.client.list_collections():
    print(f"  - {c.name}: {c.count()} documents")
