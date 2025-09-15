import os
import hmac
import hashlib
import logging
from typing import Dict, Any

from fastapi import FastAPI, Request, Header, HTTPException, status
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from a .env file for local development
load_dotenv()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Context-Aware CodeSense - GitHub Ingress",
    description="Receives and validates GitHub App webhooks.",
    version="0.1.0"
)

# --- Environment Variables & Constants ---
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
if not GITHUB_WEBHOOK_SECRET:
    logging.warning("GITHUB_WEBHOOK_SECRET is not set. Webhook validation is disabled.")

# The specific pull request actions we want to trigger a review on
SUPPORTED_PR_ACTIONS = {"opened", "reopened", "synchronize"}


# --- Helper Function for Webhook Validation ---
async def validate_github_signature(request: Request, secret: str) -> bool:
    """
    Validates the 'X-Hub-Signature-256' header to ensure the webhook is from GitHub.
    """
    signature_header = request.headers.get('X-Hub-Signature-256')
    if not signature_header:
        return False

    # The signature is of the form 'sha256=<signature>'
    sha_name, signature = signature_header.split('=', 1)
    if sha_name != 'sha256':
        return False

    # We need the raw request body for the HMAC digest
    body = await request.body()
    
    # Calculate the expected signature
    mac = hmac.new(secret.encode('utf-8'), msg=body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()

    return hmac.compare_digest(signature, expected_signature)


# --- API Endpoints ---
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}

@app.post("/api/github/webhook")
async def github_webhook_handler(
    request: Request,
    x_github_event: str = Header(...),
):
    """
    Handles incoming webhooks from the GitHub App.
    """
    # 1. Security Validation (only if secret is configured)
    if GITHUB_WEBHOOK_SECRET:
        if not await validate_github_signature(request, GITHUB_WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid X-Hub-Signature-256"
            )

    # 2. Event Filtering
    if x_github_event != "pull_request":
        logging.info(f"Ignoring '{x_github_event}' event.")
        return {"status": "event_ignored", "reason": "not_a_pull_request"}

    # 3. Payload Parsing & Action Filtering
    payload = await request.json()
    action = payload.get("action")

    if action not in SUPPORTED_PR_ACTIONS:
        logging.info(f"Ignoring pull_request action: '{action}'")
        return {"status": "action_ignored", "reason": f"action_not_supported: {action}"}

    # 4. Data Extraction
    try:
        repo_full_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        installation_id = payload["installation"]["id"]
        
        # In a real system, this is where you would dispatch the job to the next service
        # (e.g., push to a message queue like RabbitMQ or Kafka).
        # For now, we just log the extracted information.
        logging.info("🚀 Received relevant PR event. Kicking off review process...")
        logging.info(f"  - Repository: {repo_full_name}")
        logging.info(f"  - Pull Request #: {pr_number}")
        logging.info(f"  - Installation ID: {installation_id}")

        return {
            "status": "event_processed",
            "repository": repo_full_name,
            "pr_number": pr_number,
            "installation_id": installation_id
        }
    except KeyError as e:
        logging.error(f"Failed to parse required fields from payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing expected key in payload: {e}"
        )