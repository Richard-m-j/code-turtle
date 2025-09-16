## Final Project Summary: Phase 1

This phase created a "smart" indexing agent that runs in a Docker container. The process is fully automated by a GitHub Actions workflow that detects code changes, performs targeted updates to a Pinecone vector database, and publishes a versioned image of the agent to Docker Hub.

### 1\. Final Directory Structure

Your project should be organized as follows. The `.env` file is for local development only and should not be committed to Git.

```
code-turtle/
├── .github/
│   └── workflows/
│       └── indexer.yml       # The automated CI/CD workflow
│
├── scripts/
│   ├── indexer.py            # The smart indexing agent
│   └── requirements.txt      # Python dependencies for the agent
│
├── src/                      # Your project's actual source code goes here
│   └── ...
│
├── .dockerignore             # Excludes files from the Docker image
├── .gitignore                # Excludes files from Git
├── .env                      # Local secrets (DO NOT COMMIT)
└── Dockerfile                # Instructions to build the agent's container
```

-----

### 2\. File Contents

Here is the final code for each file in the project.

#### **`.github/workflows/indexer.yml`**

This workflow automates the entire process. On a push to the `main` branch, it finds changed files, builds the Docker image, runs the indexer to sync changes, and pushes the new image to Docker Hub. It can also be run manually for a full re-scan.

```yaml
name: Code-turtle Smart Indexing Agent

on:
  # Run manually for a full repository scan
  workflow_dispatch:

  # Run on pushes to main for incremental updates
  push:
    branches:
      - main

jobs:
  build-run-and-push:
    runs-on: ubuntu-latest
    
    steps:
      - name: 1. Checkout Repository
        # Fetch full history to enable accurate diff between commits
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: 2. Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: 3. Identify Changed Files
        id: changed_files
        # Only run this step for 'push' events, not manual 'workflow_dispatch'
        if: github.event_name == 'push'
        run: |
          # Get the list of added (A), modified (M), and deleted (D) files
          git diff --name-status ${{ github.event.before }} ${{ github.sha }} -- > diff.txt
          
          # Create lists for upserting and deleting
          awk '$1 ~ /^[AM]/ {print $2}' diff.txt > files_to_upsert.txt
          awk '$1 == "D" {print $2}' diff.txt > files_to_delete.txt
          
          echo "Upserting:"
          cat files_to_upsert.txt
          echo "Deleting:"
          cat files_to_delete.txt

      - name: 4. Build and Tag Docker Image
        run: |
          docker build -t ${{ secrets.DOCKERHUB_USERNAME }}/code-turtle-indexer:latest \
                       -t ${{ secrets.DOCKERHUB_USERNAME }}/code-turtle-indexer:${{ github.sha }} \
                       .

      - name: 5. Run Smart Indexing Container
        run: |
          DOCKER_OPTIONS="--rm \
            -e PINECONE_API_KEY=${{ secrets.VECTOR_DB_API_KEY }} \
            -e PINECONE_ENVIRONMENT=${{ secrets.VECTOR_DB_ENVIRONMENT }} \
            -e SCAN_PATH='/source_code'"
          
          # If this is a 'push' event, mount the diff files and point the script to them
          if [ "${{ github.event_name }}" == "push" ]; then
            DOCKER_OPTIONS="$DOCKER_OPTIONS \
              -e UPSERT_FILE_LIST='/source_code/files_to_upsert.txt' \
              -e DELETE_FILE_LIST='/source_code/files_to_delete.txt'"
          fi

          # The main volume mount is always needed
          DOCKER_OPTIONS="$DOCKER_OPTIONS \
            -v ${{ github.workspace }}:/source_code"

          # Execute the final command
          docker run $DOCKER_OPTIONS ${{ secrets.DOCKERHUB_USERNAME }}/code-turtle-indexer:latest

      - name: 6. Push Image to Docker Hub
        # Only push if the event is a push to the 'main' branch
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: |
          docker push --all-tags ${{ secrets.DOCKERHUB_USERNAME }}/code-turtle-indexer
```

#### **`Dockerfile`**

This file defines the portable container environment for the agent, installing all necessary Python dependencies.

```dockerfile
# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's layer caching
COPY scripts/requirements.txt scripts/requirements.txt

# Install the Python dependencies
RUN pip install --no-cache-dir -r scripts/requirements.txt

# Copy the rest of the application code
COPY scripts/ scripts/

# Set the default command to run when the container starts
CMD ["python", "scripts/indexer.py"]
```

#### **`scripts/indexer.py`**

This is the core agent logic. It connects to Pinecone and can perform a full scan or an intelligent sync (upsert/delete) based on file lists provided by the workflow.

```python
import os
import time
from dotenv import load_dotenv
from pinecone import Pinecone
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

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

def delete_vectors_for_files(index, file_paths):
    if not file_paths:
        return
    print(f"🗑️ Deleting vectors for {len(file_paths)} files...")
    try:
        index.delete(filter={"file_path": {"$in": file_paths}})
        print(f"✅ Successfully deleted vectors for: {', '.join(file_paths)}")
    except Exception as e:
        print(f"⚠️ Error deleting vectors: {e}")

def get_files_to_process():
    if UPSERT_FILE_LIST:
        print(f"🔍 Reading file list from: {UPSERT_FILE_LIST}")
        try:
            with open(UPSERT_FILE_LIST, 'r') as f:
                files = [line.strip() for line in f if line.strip()]
                supported_files = [f for f in files if os.path.splitext(f)[1] in SUPPORTED_EXTENSIONS]
                print(f"✅ Found {len(supported_files)} supported files to process from list.")
                return supported_files
        except FileNotFoundError:
            print(f"⚠️ File not found: {UPSERT_FILE_LIST}. Aborting.")
            return []

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
    
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    if PINECONE_INDEX_NAME not in [index['name'] for index in pc.list_indexes()]:
        print(f"❌ Pinecone index '{PINECONE_INDEX_NAME}' not found. Please create it in the console.")
        return

    index_info = pc.describe_index(PINECONE_INDEX_NAME)
    index = pc.Index(PINECONE_INDEX_NAME, host=index_info['host'])
    print("✅ Pinecone initialized.")

    files_to_delete = get_files_to_delete()
    if files_to_delete:
        delete_vectors_for_files(index, files_to_delete)

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
```

#### **`scripts/requirements.txt`**

This file lists the Python packages needed to run the agent.

```txt
pinecone
langchain
langchain-community
sentence-transformers
tree-sitter
tree-sitter-languages[python,javascript,go,typescript]
python-dotenv
tqdm
```

#### **`.dockerignore`**

This file keeps the Docker image lean by excluding unnecessary files from the build process.

```
# Git and GitHub files
.git
.github
.gitignore

# Docker files
Dockerfile
.dockerignore

# Python virtual environment and cache
.venv
__pycache__/
*.pyc

# Local secrets file
.env
```

#### **`.gitignore`**

This file prevents sensitive files and local artifacts from being committed to your repository.

```
# Byte-compiled / optimized / DLL files
__pycache__/
*.pyc
*.pyo
*.pyd

# Virtual environment
.venv/
venv/
ENV/

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Secrets
.env
```