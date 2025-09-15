# scripts/indexer.py

import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load environment variables from .env file for local development
load_dotenv()

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = "code-turtle"

EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_MODEL_DIMENSION = 384

REPO_PATH = os.getenv("SCAN_PATH", ".")
UPSERT_FILE_LIST = os.getenv("UPSERT_FILE_LIST")
DELETE_FILE_LIST = os.getenv("DELETE_FILE_LIST")

SUPPORTED_EXTENSIONS = {
    ".py": Language.PYTHON, ".js": Language.JS, ".ts": Language.TS, ".go": Language.GO,
}
FILES_TO_IGNORE = ["__init__.py", ".DS_Store"]

# --- New Deletion Logic ---
def delete_vectors_for_files(index, file_paths):
    """Deletes all vectors from Pinecone associated with the given file paths."""
    if not file_paths:
        return
    print(f"🗑️ Deleting vectors for {len(file_paths)} files...")
    try:
        # Pinecone's delete operation can filter by metadata
        index.delete(filter={"file_path": {"$in": file_paths}})
        print(f"✅ Successfully deleted vectors for: {', '.join(file_paths)}")
    except Exception as e:
        print(f"⚠️ Error deleting vectors: {e}")

# --- Modified File Discovery Logic ---
def get_files_to_process():
    """Gets a list of file paths to process, either from a file or by scanning the repo."""
    if UPSERT_FILE_LIST:
        print(f"🔍 Reading file list from: {UPSERT_FILE_LIST}")
        try:
            with open(UPSERT_FILE_LIST, 'r') as f:
                # Read files, strip whitespace, and filter out non-supported extensions
                files = [line.strip() for line in f if line.strip()]
                supported_files = [f for f in files if os.path.splitext(f)[1] in SUPPORTED_EXTENSIONS]
                print(f"✅ Found {len(supported_files)} supported files to process from list.")
                return supported_files
        except FileNotFoundError:
            print(f"⚠️ File not found: {UPSERT_FILE_LIST}. Aborting.")
            return []

    # Fallback to scanning the entire repository if no file list is provided
    print("🔍 No file list provided. Scanning entire repository...")
    found_files = []
    for root, _, files in os.walk(REPO_PATH):
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
        for file in files:
            if file in FILES_TO_IGNORE:
                continue
            if os.path.splitext(file)[1] in SUPPORTED_EXTENSIONS:
                found_files.append(os.path.join(root, file))
    print(f"✅ Found {len(found_files)} supported files by scanning.")
    return found_files

def get_files_to_delete():
    """Gets a list of file paths to delete from the vector index."""
    if not DELETE_FILE_LIST:
        return []
    print(f"🔍 Reading deletion list from: {DELETE_FILE_LIST}")
    try:
        with open(DELETE_FILE_LIST, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"⚠️ File not found: {DELETE_FILE_LIST}. No files will be deleted.")
        return []

def chunk_code_files(file_paths):
    # This function remains the same as before
    all_chunks = []
    print("🧠 Starting code chunking process...")
    for file_path in tqdm(file_paths, desc="Chunking files"):
        ext = os.path.splitext(file_path)[1]
        language = SUPPORTED_EXTENSIONS.get(ext)
        if not language: continue

        splitter = RecursiveCharacterTextSplitter.from_language(
            language=language, chunk_size=512, chunk_overlap=64
        )
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            chunks = splitter.create_documents([code])
            for chunk in chunks:
                start_line = chunk.metadata.get('start_line', 1)
                end_line = start_line + chunk.page_content.count('\n')
                chunk.metadata = {
                    "file_path": file_path, "start_line": start_line, "end_line": end_line,
                }
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"⚠️ Could not process file {file_path}: {e}")
    print(f"✅ Generated {len(all_chunks)} code chunks.")
    return all_chunks

def main():
    print("🚀 Starting Code-turtle Smart Indexing Agent...")
    
    if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
        raise ValueError("PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set.")
    
    pc = Pinecone(api_key=PINECONE_API_KEY) # Environment is now passed when getting the index
    
    # Check if index exists, but don't create it from the script
    if PINECONE_INDEX_NAME not in [index['name'] for index in pc.list_indexes()]:
        print(f"❌ Pinecone index '{PINECONE_INDEX_NAME}' not found. Please create it in the console.")
        return

    index = pc.Index(PINECONE_INDEX_NAME, host=pc.describe_index(PINECONE_INDEX_NAME)['host'])
    print("✅ Pinecone initialized.")

    # 1. Handle Deletions First
    files_to_delete = get_files_to_delete()
    if files_to_delete:
        delete_vectors_for_files(index, files_to_delete)

    # 2. Handle Upserts
    files_to_process = get_files_to_process()
    if not files_to_process:
        print("✅ No new or modified files to index. Job complete.")
        return
    
    chunks = chunk_code_files(files_to_process)
    if not chunks:
        print("✅ No content chunks generated from files. Job complete.")
        return

    print("🤖 Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("✅ Embedding model loaded.")

    print(f"📦 Upserting {len(chunks)} vectors to Pinecone in batches...")
    batch_size = 100
    for i in tqdm(range(0, len(chunks), batch_size), desc="Upserting to DB"):
        batch = chunks[i:i+batch_size]
        texts_to_embed = [chunk.page_content for chunk in batch]
        embeddings = model.encode(texts_to_embed, show_progress_bar=False).tolist()
        
        vectors_to_upsert = []
        for j, chunk in enumerate(batch):
            vector_id = f"{chunk.metadata['file_path']}::{chunk.metadata['start_line']}-{chunk.metadata['end_line']}"
            vectors_to_upsert.append({
                "id": vector_id, "values": embeddings[j], "metadata": chunk.metadata
            })
        index.upsert(vectors=vectors_to_upsert)

    print("\n🎉 Smart indexing complete!")
    stats = index.describe_index_stats()
    print(f"📊 Pinecone Index Stats: {stats['total_vector_count']} total vectors.")

if __name__ == "__main__":
    main()