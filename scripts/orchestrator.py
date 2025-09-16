# scripts/orchestrator.py

import os
import json
import subprocess
import sys
import re

def run_script(script_name, stdin_data):
    """Runs a Python script as a subprocess, passing data via stdin."""
    try:
        process = subprocess.run(
            [sys.executable, script_name],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=True
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        # Print the actual error from the failed script
        print(f"❌ Error in {script_name}:\n{e.stderr}", file=sys.stderr)
        raise

def find_new_imports(diff_text):
    """
    Parses the diff to find new import statements.
    """
    # Regex to find lines starting with '+' and containing 'import' or 'from'
    import_pattern = re.compile(r'^\+\s*(?:from\s+([a-zA-Z0-9_]+)|import\s+([a-zA-Z0-9_]+))')
    new_libraries = set()
    
    for line in diff_text.split('\n'):
        match = import_pattern.match(line)
        if match:
            # The library name will be in either group 1 or 2
            lib_name = match.group(1) or match.group(2)
            if lib_name:
                new_libraries.add(lib_name)
    
    return list(new_libraries)

def main():
    """Main orchestration logic."""
    print("🚀 Orchestrator starting...")

    # 1. Load PR context from GitHub event file
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        raise ValueError("GITHUB_EVENT_PATH environment variable not set.")
        
    with open(event_path, 'r') as f:
        event_data = json.load(f)

    pr_number = event_data['pull_request']['number']
    base_sha = event_data['pull_request']['base']['sha']
    head_sha = event_data['pull_request']['head']['sha']

    print(f"✅ Loaded context for PR #{pr_number} (Base: {base_sha[:7]}, Head: {head_sha[:7]})")

    # 2. Generate git diff
    print("📝 Generating git diff...")
    diff_process = subprocess.run(
        ['git', 'diff', f"{base_sha}...{head_sha}"],
        capture_output=True,
        text=True,
        check=True
    )
    diff_output = diff_process.stdout
    if not diff_output.strip():
        print("✅ No code changes detected. Exiting.")
        return

    # 3. Call Retriever Agent
    print("🧠 Calling Context Retriever Agent...")
    retriever_script = os.path.join(os.path.dirname(__file__), 'retriever.py')
    context_payload_str = run_script(retriever_script, diff_output)
    context_payload = json.loads(context_payload_str)
    print("✅ Context retrieved successfully.")
    
    # 4. Analyze diff for new libraries and call Web Search Agent if needed
    new_libraries = find_new_imports(diff_output)
    web_search_summary = None
    if new_libraries:
        print(f"🔍 Found new libraries: {', '.join(new_libraries)}. Calling Web Search Agent...")
        search_query = f"best practices for using {new_libraries[0]} in python"
        searcher_script = os.path.join(os.path.dirname(__file__), 'searcher.py')
        
        try:
            search_result_str = run_script(searcher_script, search_query)
            search_result = json.loads(search_result_str)
            web_search_summary = search_result.get("web_search_summary")
            if web_search_summary:
                print("✅ Web search completed successfully.")
                # Add web search results to the main context payload
                context_payload["web_search_summary"] = web_search_summary
        except Exception as e:
            print(f"⚠️  Could not get web search results: {e}", file=sys.stderr)

    # 5. Call Review Synthesizer Agent
    print("✍️ Calling Review Synthesizer Agent...")
    synthesizer_script = os.path.join(os.path.dirname(__file__), 'synthesizer.py')
    # Pass the potentially updated context_payload to the synthesizer
    review_markdown = run_script(synthesizer_script, json.dumps(context_payload))
    print("✅ Review synthesized successfully.")

    # 6. Post review comment to PR
    print(f"📤 Posting review to PR #{pr_number}...")
    review_file = "review_comment.md"
    with open(review_file, "w") as f:
        f.write(review_markdown)
    
    subprocess.run(
        ['gh', 'pr', 'comment', str(pr_number), '--body-file', review_file],
        check=True
    )
    
    os.remove(review_file)
    print("🎉 Review posted successfully! Orchestration complete.")

if __name__ == "__main__":
    main()