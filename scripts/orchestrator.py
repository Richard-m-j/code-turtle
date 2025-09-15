import os
import json
import subprocess
import sys

def run_script(script_name, stdin_data):
    """Runs a Python script as a subprocess, passing data via stdin."""
    process = subprocess.run(
        [sys.executable, script_name],
        input=stdin_data,
        capture_output=True,
        text=True,
        check=True
    )
    return process.stdout

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
    context_payload = run_script(retriever_script, diff_output)
    print("✅ Context retrieved successfully.")

    # 4. Call Review Synthesizer Agent
    print("✍️ Calling Review Synthesizer Agent...")
    synthesizer_script = os.path.join(os.path.dirname(__file__), 'synthesizer.py')
    review_markdown = run_script(synthesizer_script, context_payload)
    print("✅ Review synthesized successfully.")

    # 5. Post review comment to PR
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