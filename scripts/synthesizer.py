import os
import sys
import json
import boto3
from dotenv import load_dotenv # <--- ADD THIS LINE

load_dotenv()
# --- Configuration ---
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "us-east-1")
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

def format_context_for_prompt(file_dict, section_title):
    """Formats a dictionary of file contents into a string for the prompt."""
    if not file_dict:
        return ""
    
    prompt_section = f"\n\n## {section_title}\n\n"
    for path, content in file_dict.items():
        prompt_section += f"### File: `{path}`\n```\n{content}\n```\n\n"
    return prompt_section

def main():
    """Generates a code review using an LLM with the provided context."""
    context_payload = json.load(sys.stdin)
    
    diff = context_payload.get("diff")
    changed_files = context_payload.get("changed_files")
    retrieved_context = context_payload.get("retrieved_context")

    # Construct the prompt
    system_prompt = """
    You are "Odyssey", an expert AI code reviewer. Your purpose is to help developers write high-quality code.
    Analyze the provided context, which includes a git diff, the full content of changed files, and the content of potentially related files from the existing codebase.
    Provide a concise, constructive, and clear code review in Markdown format.
    - Start with a brief, high-level summary of the changes.
    - If you find specific issues (e.g., bugs, style violations, performance concerns, lack of documentation), create a bulleted list. For each issue, reference the file and line number if possible.
    - If there are no major issues, state that the code looks good and maybe offer a minor suggestion for improvement.
    - Be positive and encouraging. The goal is collaboration, not criticism.
    - Do NOT include the context files or the diff in your final response. Your output should only be the review itself.
    """

    user_prompt = "Please review the following pull request."
    user_prompt += f"\n\n## Pull Request Diff\n\n```diff\n{diff}\n```"
    user_prompt += format_context_for_prompt(changed_files, "Full Content of Changed Files")
    user_prompt += format_context_for_prompt(retrieved_context, "Context from Potentially Related Files")
    
    # Initialize Bedrock client
    bedrock_client = boto3.client(service_name='bedrock-runtime', region_name=AWS_REGION_NAME)
    
    # Prepare the payload for the Claude 3 model
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{
            "role": "user",
            "content": user_prompt
        }]
    })

    # Invoke the model
    try:
        response = bedrock_client.invoke_model(body=body, modelId=MODEL_ID)
        response_body = json.loads(response.get('body').read())
        review_text = response_body['content'][0]['text']
        
        # Add a header to the review
        final_review = "###  Odyssey AI Code Review 🤖\n\n" + review_text
        print(final_review)
        
    except Exception as e:
        error_message = f"Error invoking Bedrock model: {e}"
        print(error_message, file=sys.stderr)
        # Provide a fallback message to post on the PR
        print("### Odyssey AI Code Review 🤖\n\nSorry, I encountered an error while generating the review. Please check the GitHub Actions logs for details.")

if __name__ == "__main__":
    main()