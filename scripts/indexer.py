# scripts/indexer.py

import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Load environment variables from .env file for local development
load_dotenv()

# --- Configuration ---
# Vector Database (Pinecone)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = "code-turtle"

# Embedding Model
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
# This model outputs 384-dimensional vectors
EMBEDDING_MODEL_DIMENSION = 384

# Code Scanning Configuration
REPO_PATH = os.getenv("SCAN_PATH", ".") # Scan path configurable via environment variable
SUPPORTED_EXTENSIONS = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".ts": Language.TS,
    ".go": Language.GO,
    # Add other extensions and their corresponding LangChain Language enum here
}
FILES_TO_IGNORE = ["__init__.py", ".DS_Store"]

# --- Main Indexing Logic ---

def get_code_files():
    """Scans the repository and returns a list of file paths for supported code files."""
    found_files = []
    for root, _, files in os.walk(REPO_PATH):
        # Ignore hidden directories like .git, .github
        if any(part.startswith('.') for part in root.split(os.sep)):
            continue
        for file in files:
            if file in FILES_TO_IGNORE:
                continue
            ext = os.path.splitext(file)[1]
            if ext in SUPPORTED_EXTENSIONS:
                found_files.append(os.path.join(root, file))
    print(f"✅ Found {len(found_files)} supported code files.")
    return found_files

def chunk_code_files(file_paths):
    """Loads and chunks code files using a language-aware splitter."""
    all_chunks = []
    print("🧠 Starting code chunking process...")
    for file_path in tqdm(file_paths, desc="Chunking files"):
        ext = os.path.splitext(file_path)[1]
        language = SUPPORTED_EXTENSIONS[ext]
        
        # Using a text splitter designed for code
        # This splitter tries to keep functions, classes, and other logical blocks together
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=language, chunk_size=512, chunk_overlap=64
        )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            chunks = splitter.create_documents([code])
            
            # Add file path metadata to each chunk
            for i, chunk in enumerate(chunks):
                # LangChain's splitter adds 'loc' (lines of code) metadata
                start_line = chunk.metadata.get('start_line', 1)
                
                # Simple way to calculate end line based on lines in the chunk
                end_line = start_line + chunk.page_content.count('\n')

                chunk.metadata = {
                    "file_path": file_path,
                    "start_line": start_line,
                    "end_line": end_line,
                    # Storing content hash can help detect unchanged chunks in the future
                    "content_hash": hash(chunk.page_content), 
                }
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"⚠️ Could not process file {file_path}: {e}")

    print(f"✅ Generated {len(all_chunks)} code chunks.")
    return all_chunks

def main():
    """Main function to run the indexing process."""
    print("🚀 Starting Code-turtle Indexing Agent...")
    
    # 1. Initialize Vector DB
    if not PINECONE_API_KEY or not PINECONE_ENVIRONMENT:
        raise ValueError("PINECONE_API_KEY and PINECONE_ENVIRONMENT must be set.")
        
    pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    
    if PINECONE_INDEX_NAME not in pc.list_indexes().names():
        print(f"🚧 Pinecone index '{PINECONE_INDEX_NAME}' not found. Creating it...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_MODEL_DIMENSION,
            metric='cosine' # 'cosine' is great for semantic similarity
        )
        time.sleep(1) # Wait for index to be ready
    
    index = pc.Index(PINECONE_INDEX_NAME)
    print("✅ Pinecone initialized.")

    # 2. Initialize Embedding Model
    print("🤖 Loading embedding model...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    print("✅ Embedding model loaded.")

    # 3. Find and Chunk Code
    files = get_code_files()
    if not files:
        print("No code files found to index. Exiting.")
        return
        
    chunks = chunk_code_files(files)
    if not chunks:
        print("No chunks were generated. Exiting.")
        return

    # 4. Generate Embeddings and Upsert to Vector DB
    print(f"📦 Upserting {len(chunks)} vectors to Pinecone in batches...")
    batch_size = 100
    for i in tqdm(range(0, len(chunks), batch_size), desc="Upserting to DB"):
        batch = chunks[i:i+batch_size]
        
        # Get the text content for embedding
        texts_to_embed = [chunk.page_content for chunk in batch]
        
        # Generate embeddings
        embeddings = model.encode(texts_to_embed, show_progress_bar=False).tolist()
        
        # Prepare vectors for upsert, ensuring NO source code is included
        vectors_to_upsert = []
        for j, chunk in enumerate(batch):
            vector_id = f"{chunk.metadata['file_path']}::{chunk.metadata['start_line']}-{chunk.metadata['end_line']}"
            vectors_to_upsert.append({
                "id": vector_id,
                "values": embeddings[j],
                "metadata": chunk.metadata  # Contains only file_path, line numbers, and hash
            })

        # Upsert the batch
        index.upsert(vectors=vectors_to_upsert)

    print("\n🎉 Indexing complete! Your codebase memory is ready.")
    stats = index.describe_index_stats()
    print(f"📊 Pinecone Index Stats: {stats['total_vector_count']} total vectors.")


if __name__ == "__main__":
    main()