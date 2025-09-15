import os
import sys
import json
import re
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# --- Configuration ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = "code-turtle"
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
TOP_K = 7 # Number of similar code chunks to retrieve

def parse_diff(diff_text):
    """Parses git diff to extract added lines and changed file paths."""
    added_lines = []
    changed_files = set()
    
    # Regex to find file paths in diff header
    file_path_pattern = re.compile(r'^\+\+\+ b/(.*)$', re.MULTILINE)
    for match in file_path_pattern.finditer(diff_text):
        changed_files.add(match.group(1))

    for line in diff_text.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            added_lines.append(line[1:]) # Store without the '+'
            
    return list(changed_files), added_lines

def read_file_content(file_path):
    """Safely reads the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️  Warning: File not found during context retrieval: {file_path}")
        return None
    except Exception as e:
        print(f"⚠️  Warning: Error reading file {file_path}: {e}")
        return None

def main():
    """Retrieves context based on the provided diff."""
    diff_text = sys.stdin.read()
    
    changed_file_paths, added_lines = parse_diff(diff_text)
    
    if not added_lines:
        print("No added lines to analyze.", file=sys.stderr)
        # Still return changed files for context
        context_payload = {
            "diff": diff_text,
            "changed_files": {path: read_file_content(path) for path in changed_file_paths if read_file_content(path)},
            "retrieved_context": {}
        }
        print(json.dumps(context_payload))
        return

    # Initialize model and Pinecone
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(PINECONE_INDEX_NAME)

    # Embed the new code
    query_text = "\n".join(added_lines)
    query_vector = model.encode(query_text).tolist()

    # Query Pinecone
    query_results = index.query(vector=query_vector, top_k=TOP_K, include_metadata=True)
    
    # Gather retrieved file paths
    retrieved_files = set()
    for match in query_results['matches']:
        file_path = match['metadata'].get('file_path')
        if file_path:
            retrieved_files.add(file_path)
            
    # Combine all unique file paths
    all_context_paths = set(changed_file_paths).union(retrieved_files)

    # Prepare final payload
    context_payload = {
        "diff": diff_text,
        "changed_files": {
            path: read_file_content(path) 
            for path in changed_file_paths 
            if read_file_content(path) is not None
        },
        "retrieved_context": {
            path: read_file_content(path) 
            for path in retrieved_files 
            if read_file_content(path) is not None
        }
    }
    
    # Output JSON to stdout
    print(json.dumps(context_payload, indent=2))

if __name__ == "__main__":
    main()