# scripts/searcher.py

import os
import sys
import json
import serpapi
from dotenv import load_dotenv 

load_dotenv() 

def summarize_results(results):
    """
    Summarizes the top organic search results.
    """
    summary = ""
    if "organic_results" in results:
        for i, result in enumerate(results["organic_results"][:3]): # Summarize top 3
            title = result.get("title", "No Title")
            link = result.get("link", "#")
            snippet = result.get("snippet", "No snippet available.")
            summary += f"### Result {i+1}: {title}\n"
            summary += f"**Link:** {link}\n"
            summary += f"**Snippet:** {snippet}\n\n"
    return summary.strip() if summary else "No relevant search results found."

def main():
    """
    Performs a web search based on a query from stdin and prints a summary.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        print("Error: SERPAPI_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    query = sys.stdin.read().strip()
    if not query:
        print("Error: No search query provided.", file=sys.stderr)
        sys.exit(1)

    try:
        client = serpapi.Client(api_key=api_key)
        
        params = {
            "q": query,
            "engine": "google",
            "gl": "us",
            "hl": "en"
        }
        
        results = client.search(params)
        
        summary = summarize_results(results)
        
        output = {"web_search_summary": summary}
        print(json.dumps(output, indent=2))

    except Exception as e:
        print(f"An error occurred during the web search: {e}", file=sys.stderr)
        error_output = {"web_search_summary": f"An error occurred: {e}"}
        print(json.dumps(error_output, indent=2))


if __name__ == "__main__":
    main()