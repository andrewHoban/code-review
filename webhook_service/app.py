# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main Flask application for GitHub webhook service."""

import hashlib
import hmac
import json
import logging
import os

from agent_client import AgentEngineClient
from comment_poster import CommentPoster
from config import Config
from config_loader import ConfigLoader
from context_extractor import extract_review_context
from flask import Flask, jsonify, request
from github_client import GitHubClient
from installation_manager import InstallationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load secrets on startup
try:
    Config.load_secrets()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.warning(f"Could not load all secrets: {e}. Some features may not work.")

# Initialize clients
github_client = None
agent_client = None
comment_poster = None
installation_manager = None
config_loader = None

try:
    github_client = GitHubClient()
    agent_client = AgentEngineClient()
    comment_poster = CommentPoster(github_client)
    installation_manager = InstallationManager()
    config_loader = ConfigLoader(github_client)
    logger.info("All clients initialized successfully")
except Exception as e:
    logger.warning(f"Could not initialize clients: {e}")


def verify_webhook_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """Verify that the webhook request came from GitHub."""
    if not signature_header:
        logger.warning("No signature header provided")
        return False

    if not Config.GITHUB_WEBHOOK_SECRET:
        logger.warning("Webhook secret not configured, skipping signature verification")
        return True  # Allow in development mode

    hash_object = hmac.new(
        Config.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256,
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)


@app.route("/webhook", methods=["POST"])
def webhook_handler():
    """Handle incoming webhook events from GitHub."""
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_webhook_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 403

    # Parse event
    event_type = request.headers.get("X-GitHub-Event")
    payload = request.json

    logger.info(f"Received {event_type} event")
    logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

    # Handle installation events
    if event_type == "installation":
        action = payload.get("action")
        installation_id = payload.get("installation", {}).get("id")
        repositories = [
            repo.get("full_name") for repo in payload.get("repositories", [])
        ]

        if action == "created" and installation_manager:
            logger.info(f"App installed: {installation_id}, repos: {repositories}")
            installation_manager.add_installation(installation_id, repositories)
        elif action == "deleted" and installation_manager:
            logger.info(f"App uninstalled: {installation_id}")
            installation_manager.remove_installation(installation_id)

    elif event_type == "installation_repositories":
        action = payload.get("action")
        installation_id = payload.get("installation", {}).get("id")

        if action == "added" and installation_manager:
            added_repos = [
                repo.get("full_name") for repo in payload.get("repositories_added", [])
            ]
            logger.info(
                f"Repositories added to installation {installation_id}: {added_repos}"
            )
            # Get current repos and update
            installation = installation_manager.get_installation(installation_id)
            current_repos = installation.get("repositories", []) if installation else []
            installation_manager.update_installation_repositories(
                installation_id, current_repos + added_repos
            )
        elif action == "removed" and installation_manager:
            removed_repos = [
                repo.get("full_name")
                for repo in payload.get("repositories_removed", [])
            ]
            logger.info(
                f"Repositories removed from installation {installation_id}: {removed_repos}"
            )
            # Get current repos and update
            installation = installation_manager.get_installation(installation_id)
            current_repos = installation.get("repositories", []) if installation else []
            updated_repos = [r for r in current_repos if r not in removed_repos]
            installation_manager.update_installation_repositories(
                installation_id, updated_repos
            )

    # Handle pull request events
    elif event_type == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize", "reopened"]:
            # Skip draft PRs
            if payload.get("pull_request", {}).get("draft", False):
                logger.info("Skipping draft PR")
                return jsonify({"status": "skipped - draft PR"}), 200

            # Extract context
            installation_id = payload.get("installation", {}).get("id")
            repo_full_name = payload.get("repository", {}).get("full_name")
            pr_number = payload.get("pull_request", {}).get("number")

            if not installation_id or not repo_full_name or not pr_number:
                logger.error("Missing required PR data in webhook payload")
                return jsonify({"error": "Missing required PR data"}), 400

            logger.info(f"Extracting context for PR {repo_full_name}#{pr_number}")

            try:
                if not github_client:
                    raise ValueError("GitHub client not initialized")

                # Load repository configuration
                if config_loader:
                    base_branch = (
                        payload.get("pull_request", {})
                        .get("base", {})
                        .get("ref", "main")
                    )
                    repo_config = config_loader.load_repo_config(
                        installation_id, repo_full_name, base_branch
                    )

                    # Check if reviews are enabled
                    if not repo_config.get("enabled", True):
                        logger.info(f"Reviews disabled for {repo_full_name}")
                        return jsonify({"status": "skipped - reviews disabled"}), 200

                review_context = extract_review_context(
                    installation_id,
                    repo_full_name,
                    pr_number,
                    payload.get("pull_request", {}),
                    github_client,
                )

                logger.info(
                    f"Context extracted: {len(review_context['review_context']['changed_files'])} files"
                )

                # Call Agent Engine
                if not agent_client:
                    raise ValueError("Agent Engine client not initialized")

                logger.info(f"Calling Agent Engine for PR {repo_full_name}#{pr_number}")
                review_response = agent_client.review_pr(review_context)

                # Post comments
                if not comment_poster:
                    raise ValueError("Comment poster not initialized")

                logger.info("Posting review comments")
                comment_poster.post_review(
                    installation_id,
                    repo_full_name,
                    pr_number,
                    review_response,
                )

                logger.info(f"Review completed for PR {repo_full_name}#{pr_number}")

            except Exception as e:
                logger.error(f"Error processing PR: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

    return jsonify({"status": "processed"}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run."""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
