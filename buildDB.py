import os
import chromadb
from chromadb.utils import embedding_functions

# Setup Database
chroma_client = chromadb.PersistentClient(path="./university_db")
embedding_func = embedding_functions.DefaultEmbeddingFunction()

collection = chroma_client.get_or_create_collection(
    name="university_info",
    embedding_function=embedding_func
)

INPUT_DIR = "university_docs"

documents = []
metadatas = []
ids = []

print("📂 Reading text files...")

for filename in os.listdir(INPUT_DIR):
    if filename.endswith(".txt"):
        filepath = os.path.join(INPUT_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
            # Simple Chunking (Split by 1000 characters)
            chunk_size = 1000
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                
                documents.append(chunk)
                metadatas.append({"source": filename})
                ids.append(f"{filename}_{i}")

if documents:
    print(f"💾 Adding {len(documents)} chunks to the database...")
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print("✅ Database built successfully!")
else:
    print("⚠️ No documents found! Did you run crawl.py?")