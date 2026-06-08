"""Run the indexing pipeline and save output to a log file."""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Reconfigure stdout for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Redirect output to log file
log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'indexing_output.log')
sys.stdout = open(log_path, 'w', encoding='utf-8')
sys.stderr = sys.stdout

print("=" * 70)
print("STARTING ISLAMIC RAG INDEXING PIPELINE")
print("=" * 70)

import time
start = time.time()

from src.core.islamic_vectorDB import IslamicVectorStore
from src.core.islamic_chunker import get_hadith_splitter, split_with_metadata
from scripts.load_quran import load_quran_from_api
from scripts.load_hadiths import load_hadith_collection

HADITH_BOOKS = ["bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah"]

# Step 1: Initialize vector store
print("\nStep 1: Initializing vector store...")
vs = IslamicVectorStore()
print("Vector store ready!")

# Step 2: Index Quran
print("\n" + "=" * 70)
print("Step 2: Loading and indexing Quran...")
quran_docs = load_quran_from_api()
print(f"Loaded {len(quran_docs)} ayahs from API")

vs.index_documents("quran", quran_docs)
print("Quran indexing complete!")

# Step 3: Index Hadith
print("\n" + "=" * 70)
print("Step 3: Loading and indexing Hadith collections...")
splitter = get_hadith_splitter()

for book in HADITH_BOOKS:
    print(f"\n--- Indexing {book.title()} ---")
    try:
        docs = load_hadith_collection(book)
        print(f"Loaded {len(docs)} hadiths")
        
        chunks = split_with_metadata(docs, splitter)
        print(f"Split into {len(chunks)} chunks")
        
        col_name = f"hadith_{book}"
        vs.index_documents(col_name, chunks)
        print(f"OK - {book.title()} indexed!")
    except Exception as e:
        print(f"ERROR indexing {book}: {e}")

elapsed = time.time() - start
print("\n" + "=" * 70)
print(f"ALL DONE! Total time: {elapsed:.1f} seconds")
print("=" * 70)
