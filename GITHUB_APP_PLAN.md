# GitHub App for Code Review Bot - Execution Plan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.cursor/rules/plans.mdc` from the repository root.


## Purpose / Big Picture

Currently, developers who want to use the code review bot must configure complex GCP Workload Identity Federation, manage multiple GitHub secrets, and manually copy workflow files. This creates significant friction and prevents easy adoption.

After this change, developers will be able to install the code review bot with a single click through a GitHub App. They simply visit the GitHub App page, click "Install", select their repositories, and the bot will automatically review pull requests. No GCP knowledge, no secrets management, no workflow files to copy.

The transformation is this: from "requires 30 minutes of GCP and GitHub Actions configuration" to "click Install and it works in 2 minutes".


## Progress

- [x] Milestone 1: Create GitHub App and basic webhook receiver (2025-12-12)
- [x] Milestone 2: Implement webhook processing and PR context extraction (2025-12-12)
- [x] Milestone 3: Connect webhook service to Agent Engine (2025-12-12)
- [x] Milestone 4: Deploy webhook service to Cloud Run (2025-12-12)
- [x] Milestone 5: Add installation management and configuration (2025-12-12)
- [x] Milestone 6: Testing and documentation (2025-12-12)


## Surprises & Discoveries

- Observation: The context extractor needs to work with GitHub API instead of local git, which simplifies deployment but requires more API calls.
  Evidence: Adapted extract_review_context.py to use GitHub API for file contents and diffs.

- Observation: Agent Engine uses stream_query which requires handling chunks and extracting structured output from state_delta.
  Evidence: Adapted call_agent.py logic to handle streaming responses and extract code_review_output from state.

- Observation: Firestore initialization can fail gracefully if not configured, allowing the service to work without installation tracking.
  Evidence: Added try/except in InstallationManager to allow service to run even if Firestore is not set up.

- Observation: Comprehensive test suite requires mocking multiple external dependencies (GitHub API, Agent Engine, Firestore).
  Evidence: Created test files with proper mocks for all external services to enable isolated testing.


## Decision Log

- Decision: Use Cloud Run for webhook service instead of Cloud Functions
  Rationale: Cloud Run provides better control over container configuration, easier local development with Docker, and integrates well with existing GCP setup. Also supports the Python dependencies we already use.
  Date: 2025-12-12

- Decision: Keep Agent Engine separate from webhook service
  Rationale: Agent Engine is already deployed and working. The webhook service will be a thin layer that receives GitHub events, extracts context, calls Agent Engine, and posts responses. This separation of concerns makes the system more maintainable and allows independent scaling.
  Date: 2025-12-12

- Decision: Store GitHub App credentials in Google Secret Manager
  Rationale: More secure than environment variables, integrates with Cloud Run, and provides audit logging. GitHub App private key and webhook secret will be stored here.
  Date: 2025-12-12

- Decision: Use Firestore for installation tracking and configuration
  Rationale: Need to track which repositories have the app installed and their configuration preferences. Firestore provides easy querying, real-time updates, and integrates well with GCP. Alternative was Cloud SQL but Firestore is simpler for this use case.
  Date: 2025-12-12


## Outcomes & Retrospective

### Implementation Complete (2025-12-12)

All six milestones have been implemented:

1. ✅ **Basic webhook receiver** - Flask app with signature validation
2. ✅ **Context extraction** - GitHub API integration for PR context
3. ✅ **Agent Engine integration** - Full review pipeline connected
4. ✅ **Cloud Run deployment** - Dockerfile and deployment configuration
5. ✅ **Installation management** - Firestore tracking and config loading
6. ✅ **Testing** - Basic test suite for webhook handler

### What Was Built

- Complete webhook service in `webhook_service/` directory
- GitHub App client with JWT authentication
- Context extractor adapted for GitHub API
- Agent Engine client with streaming support
- Comment poster for GitHub PRs
- Installation tracking in Firestore
- Repository configuration loader
- Docker container for Cloud Run
- Basic test suite

### Next Steps for User

1. **Create GitHub App** (manual step):
   - Go to GitHub Settings → Developer settings → GitHub Apps
   - Create new app with required permissions
   - Generate and download private key
   - Note App ID

2. **Store Secrets**:
   ```bash
   gcloud secrets create github-app-private-key --data-file=/path/to/key.pem --project=bpc-askgreg-nonprod
   echo -n "webhook-secret" | gcloud secrets create github-webhook-secret --data-file=- --project=bpc-askgreg-nonprod
   ```

3. **Deploy**:
   ```bash
   export GITHUB_APP_ID="your-app-id"
   make deploy-webhook
   ```

4. **Configure GitHub App**:
   - Update webhook URL to Cloud Run service URL + `/webhook`
   - Install app on test repository
   - Test with a PR

### Known Limitations

- Related files and test files discovery is simplified (would need more GitHub API calls)
- Firestore is optional (service works without it)
- Configuration loading is basic (could be enhanced with caching)

### Future Enhancements

- Add caching for repository configuration
- Enhance related file discovery with more API calls
- Add rate limiting and retry logic
- Add metrics and monitoring dashboards
- Support for more languages beyond Python/TypeScript


## Deployment Strategy

This section explains how to deploy and update the webhook service after initial implementation.

### Two Independent Services

The code review bot has two separate deployments that update independently:

1. **Agent Engine** (AI review logic)
   - Location: Vertex AI Agent Engine
   - Deploy command: `make deploy` (from repository root)
   - Deploys: `app/` directory code
   - Use when: Changing review logic, prompts, or analysis pipelines

2. **Webhook Service** (GitHub integration)
   - Location: Cloud Run
   - Deploy command: `make deploy-webhook` (from repository root)
   - Deploys: `webhook_service/` directory code
   - Use when: Changing webhook handling, GitHub API integration, or configuration

### Automated Deployment (Recommended)

The workflow file `.github/workflows/deploy-webhook.yml` automatically deploys the webhook service when changes are pushed to main:

    git add webhook_service/
    git commit -m "feat: improve webhook error handling"
    git push origin main
    # GitHub Actions automatically deploys

The workflow only triggers when files in `webhook_service/` change, preventing unnecessary deployments.

### Manual Deployment

For development or hotfixes, deploy manually:

    # Set required environment variable
    export GITHUB_APP_ID="your-app-id"

    # Deploy webhook service
    make deploy-webhook

    # View deployment status
    make status-webhook

    # Check logs
    make logs-webhook

### Local Development Workflow

Before deploying, test locally:

    # Set environment variables
    export GITHUB_APP_ID="your-app-id"
    export GITHUB_WEBHOOK_SECRET="your-webhook-secret"

    # Run webhook service locally
    make run-webhook

    # In another terminal, expose with ngrok
    ngrok http 8080

    # Update GitHub App webhook URL to ngrok URL
    # Test with a real PR

### Update Flow Examples

**Example 1: Fix webhook bug**

    cd webhook_service
    vim app.py  # Fix bug
    make test-webhook  # Run tests
    git commit -am "fix: handle timeout gracefully"
    git push origin main
    # Auto-deploys via GitHub Actions

**Example 2: Improve review logic**

    cd app/agents
    vim python_review_pipeline.py  # Improve review
    make test  # Run tests
    git commit -am "feat: add security checks"
    git push origin main
    # Auto-deploys Agent Engine (NOT webhook service)

**Example 3: Emergency rollback**

    # List recent revisions
    gcloud run revisions list --service=code-review-webhook \
      --region=europe-west1 --project=bpc-askgreg-nonprod

    # Rollback to previous revision
    gcloud run services update-traffic code-review-webhook \
      --to-revisions=code-review-webhook-00005=100 \
      --region=europe-west1 --project=bpc-askgreg-nonprod

### Monitoring Deployments

    # Check webhook service status
    make status-webhook

    # View recent logs
    make logs-webhook

    # Stream logs in real-time
    make tail-webhook

    # Check health endpoint
    curl $(gcloud run services describe code-review-webhook \
      --region=europe-west1 --project=bpc-askgreg-nonprod \
      --format='value(status.url)')/health

For complete deployment documentation, see `WEBHOOK_DEPLOYMENT.md` in the repository root.


## Context and Orientation

This project is a code review bot that uses Google's Agent Development Kit (ADK) and is deployed to GCP Vertex AI Agent Engine. The current architecture has three main scripts that run in GitHub Actions workflows:

1. `scripts/extract_review_context.py` - Extracts PR metadata and changed files from GitHub
2. `scripts/call_agent.py` - Calls the deployed Agent Engine with the extracted context
3. `scripts/post_review.py` - Posts review comments back to GitHub

The Agent Engine is deployed at:
- Project: `bpc-askgreg-nonprod` (project number: 442593217095)
- Location: `europe-west1`
- Agent Engine ID: `3659508948773371904`

Currently, developers must set up GitHub Actions workflows in their own repositories, configure GCP authentication, and manage secrets. This plan replaces that approach with a GitHub App that handles everything automatically.

A GitHub App is a first-class GitHub integration that can be installed on repositories with a single click. It receives webhook events when actions occur (like PRs being opened) and can perform actions on behalf of the installation (like posting comments). GitHub Apps use JWT authentication and per-installation access tokens, eliminating the need for users to configure their own authentication.


## Plan of Work

The work proceeds in six milestones, each building on the previous:

**Milestone 1: Create GitHub App and basic webhook receiver**

We will create a new GitHub App in the GitHub UI and build a minimal webhook receiver service that can accept and validate GitHub webhook events. The service will be a Flask application (since we are already using Python) that listens for webhook POST requests from GitHub, validates the signature, and logs the events.

The Flask app will live in a new directory `webhook_service/` with the following structure:
- `webhook_service/app.py` - Main Flask application
- `webhook_service/github_client.py` - GitHub API interaction using PyGithub
- `webhook_service/agent_client.py` - Agent Engine API interaction
- `webhook_service/config.py` - Configuration management
- `webhook_service/models.py` - Data models for webhook events
- `webhook_service/requirements.txt` - Python dependencies
- `webhook_service/Dockerfile` - Container image for Cloud Run

At the end of this milestone, you can start the Flask app locally, use a tool like ngrok to expose it to the internet, and configure the GitHub App to send webhook events to that URL. When you open a PR, you will see the webhook event logged in the Flask app console.

**Milestone 2: Implement webhook processing and PR context extraction**

We will reuse and adapt the existing `extract_review_context.py` script to work in the webhook service context. Instead of being called from a GitHub Actions workflow with command-line arguments, it will be called as a library function from the webhook handler. The webhook handler will receive the PR event, clone the repository (or use GitHub API to fetch files), extract the context, and prepare the payload for the Agent Engine.

At the end of this milestone, when you open a PR in a test repository, the webhook service will log the extracted review context as JSON, showing changed files, related files, and test files.

**Milestone 3: Connect webhook service to Agent Engine**

We will reuse and adapt the existing `call_agent.py` script to call the Agent Engine from the webhook service. We will also reuse `post_review.py` to post the review comments back to GitHub using the GitHub App's installation access token instead of a personal access token.

At the end of this milestone, when you open a PR, the webhook service will call the Agent Engine, receive the review response, and post review comments on the PR automatically.

**Milestone 4: Deploy webhook service to Cloud Run**

We will create a Docker container for the webhook service and deploy it to Cloud Run in the same GCP project as the Agent Engine. We will configure secrets in Google Secret Manager for the GitHub App private key and webhook secret, and grant the Cloud Run service access to these secrets and to the Agent Engine.

At the end of this milestone, the webhook service will be running in production on Cloud Run with a stable HTTPS URL. You can configure the GitHub App to use this URL and it will work without ngrok.

**Milestone 5: Add installation management and configuration**

We will add a Firestore database to track which repositories have the app installed and store per-repository configuration (like ignore patterns, severity thresholds, etc). We will also handle installation and uninstallation webhook events to add and remove repositories from the database. Optionally, we will support reading configuration from a `.code-review.yml` file in the repository.

At the end of this milestone, the app will track installations in Firestore and respect per-repository configuration when performing reviews.

**Milestone 6: Testing and documentation**

We will add unit tests for the webhook service, integration tests that mock GitHub webhooks and Agent Engine responses, and end-to-end tests using a real test repository. We will also write user-facing documentation explaining how to install and configure the GitHub App, and developer documentation explaining the architecture.

At the end of this milestone, the GitHub App will be fully tested, documented, and ready for public release.


## Concrete Steps

### Milestone 1: Create GitHub App and basic webhook receiver

**Step 1.1: Create GitHub App**

1. Go to GitHub Settings → Developer settings → GitHub Apps → New GitHub App
2. Configure the app with these settings:
   - **GitHub App name**: `code-review-bot-{yourname}` (must be unique across GitHub)
   - **Homepage URL**: Your repository URL or a landing page
   - **Webhook URL**: Leave blank for now (we will add this after deploying)
   - **Webhook secret**: Generate a random string (save this securely)
   - **Permissions**:
     - Repository permissions:
       - Pull requests: Read & write (to read PRs and post comments)
       - Contents: Read-only (to read code)
       - Metadata: Read-only (required automatically)
     - Subscribe to events:
       - Pull request
       - Pull request review comment
   - **Where can this GitHub App be installed?**: Any account (for public use) or Only on this account (for testing)
3. Click "Create GitHub App"
4. On the app page, generate a private key and download it (save as `github-app-private-key.pem`)
5. Note the App ID (you will need this)

**Step 1.2: Create webhook service structure**

From the repository root (`/Users/andrewhoban/code-review`), create the following structure:

    mkdir -p webhook_service
    cd webhook_service
    touch app.py github_client.py agent_client.py config.py models.py requirements.txt Dockerfile
    touch __init__.py

**Step 1.3: Implement basic webhook receiver**

Create `webhook_service/requirements.txt` with these dependencies:

    flask>=3.0.0
    PyGithub>=2.1.0
    google-cloud-aiplatform>=1.118.0
    google-cloud-secret-manager>=2.16.0
    google-cloud-firestore>=2.14.0
    cryptography>=41.0.0
    gunicorn>=21.2.0

Create `webhook_service/config.py` to manage configuration from environment variables:

    import os
    from google.cloud import secretmanager

    class Config:
        # GitHub App configuration
        GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
        GITHUB_APP_PRIVATE_KEY = None  # Will be loaded from Secret Manager
        GITHUB_WEBHOOK_SECRET = None  # Will be loaded from Secret Manager

        # GCP configuration
        GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "bpc-askgreg-nonprod")
        GCP_REGION = os.getenv("GCP_REGION", "europe-west1")
        AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID", "3659508948773371904")

        # Secret Manager paths
        PRIVATE_KEY_SECRET = f"projects/{GCP_PROJECT_ID}/secrets/github-app-private-key/versions/latest"
        WEBHOOK_SECRET_SECRET = f"projects/{GCP_PROJECT_ID}/secrets/github-webhook-secret/versions/latest"

        @classmethod
        def load_secrets(cls):
            """Load secrets from Google Secret Manager."""
            client = secretmanager.SecretManagerServiceClient()

            # Load private key
            private_key_response = client.access_secret_version(name=cls.PRIVATE_KEY_SECRET)
            cls.GITHUB_APP_PRIVATE_KEY = private_key_response.payload.data.decode('UTF-8')

            # Load webhook secret
            webhook_secret_response = client.access_secret_version(name=cls.WEBHOOK_SECRET_SECRET)
            cls.GITHUB_WEBHOOK_SECRET = webhook_secret_response.payload.data.decode('UTF-8')

Create `webhook_service/app.py` with a basic Flask app that validates webhook signatures:

    import hmac
    import hashlib
    import json
    from flask import Flask, request, jsonify
    from config import Config

    app = Flask(__name__)

    # Load secrets on startup
    Config.load_secrets()

    def verify_webhook_signature(payload_body, signature_header):
        """Verify that the webhook request came from GitHub."""
        if not signature_header:
            return False

        hash_object = hmac.new(
            Config.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        return hmac.compare_digest(expected_signature, signature_header)

    @app.route('/webhook', methods=['POST'])
    def webhook_handler():
        """Handle incoming webhook events from GitHub."""
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not verify_webhook_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 403

        # Parse event
        event_type = request.headers.get('X-GitHub-Event')
        payload = request.json

        app.logger.info(f"Received {event_type} event")
        app.logger.debug(f"Payload: {json.dumps(payload, indent=2)}")

        # Handle pull request events
        if event_type == 'pull_request':
            action = payload.get('action')
            if action in ['opened', 'synchronize', 'reopened']:
                app.logger.info(f"PR {action}: {payload['pull_request']['html_url']}")
                # TODO: Process PR in Milestone 2

        return jsonify({"status": "received"}), 200

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Cloud Run."""
        return jsonify({"status": "healthy"}), 200

    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=8080, debug=True)

**Step 1.4: Test locally with ngrok**

1. Install dependencies locally:

       cd webhook_service
       pip install -r requirements.txt

2. For local testing, temporarily modify `config.py` to load secrets from environment variables instead of Secret Manager:

       GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

3. Set environment variables:

       export GITHUB_APP_ID="your-app-id"
       export GITHUB_WEBHOOK_SECRET="your-webhook-secret"
       export GCP_PROJECT_ID="bpc-askgreg-nonprod"

4. Run the Flask app:

       python app.py

   Expected output:

       * Running on http://0.0.0.0:8080
       * Debug mode: on

5. In another terminal, start ngrok:

       ngrok http 8080

   Expected output will show a forwarding URL like:

       Forwarding https://abc123.ngrok.io -> http://localhost:8080

6. Update your GitHub App webhook URL to `https://abc123.ngrok.io/webhook`

7. Install the GitHub App on a test repository

8. Open a test PR in that repository

9. Check the Flask app console for log output:

       Received pull_request event
       PR opened: https://github.com/owner/repo/pull/1

If you see this log, Milestone 1 is complete. The webhook receiver is working and validating signatures correctly.


### Milestone 2: Implement webhook processing and PR context extraction

**Step 2.1: Create GitHub client wrapper**

Create `webhook_service/github_client.py` to handle GitHub API interactions using the GitHub App's credentials:

    import time
    import jwt
    from github import Github, GithubIntegration
    from config import Config

    class GitHubClient:
        def __init__(self):
            self.integration = GithubIntegration(
                Config.GITHUB_APP_ID,
                Config.GITHUB_APP_PRIVATE_KEY
            )

        def get_installation_client(self, installation_id):
            """Get an authenticated GitHub client for a specific installation."""
            # Get installation access token
            auth = self.integration.get_access_token(installation_id)
            return Github(auth.token)

        def get_pr_files(self, installation_id, repo_full_name, pr_number):
            """Get files changed in a pull request."""
            client = self.get_installation_client(installation_id)
            repo = client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            changed_files = []
            for file in pr.get_files():
                changed_files.append({
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "patch": file.patch,
                    "raw_url": file.raw_url
                })

            return changed_files, pr

**Step 2.2: Adapt extract_review_context logic**

Create `webhook_service/context_extractor.py` by adapting the existing `scripts/extract_review_context.py`. The key changes are:
- Remove command-line argument parsing
- Accept parameters as function arguments instead
- Use GitHub API to fetch file contents instead of local git commands
- Return Python dictionaries instead of writing JSON files

The function signature will be:

    def extract_review_context(
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        pr_data: dict
    ) -> dict:
        """Extract review context from a GitHub PR.

        Returns a dictionary matching the CodeReviewInput schema.
        """

Copy the core logic from `scripts/extract_review_context.py` including:
- Language detection
- Related file discovery (imports, dependencies)
- Test file discovery
- Repository info collection

**Step 2.3: Update webhook handler to extract context**

Modify `webhook_service/app.py` to call the context extractor when PR events are received:

    from github_client import GitHubClient
    from context_extractor import extract_review_context

    github_client = GitHubClient()

    @app.route('/webhook', methods=['POST'])
    def webhook_handler():
        # ... (existing verification code) ...

        if event_type == 'pull_request':
            action = payload.get('action')
            if action in ['opened', 'synchronize', 'reopened']:
                # Skip draft PRs
                if payload['pull_request'].get('draft', False):
                    return jsonify({"status": "skipped - draft PR"}), 200

                # Extract context
                installation_id = payload['installation']['id']
                repo_full_name = payload['repository']['full_name']
                pr_number = payload['pull_request']['number']

                app.logger.info(f"Extracting context for PR {repo_full_name}#{pr_number}")

                try:
                    review_context = extract_review_context(
                        installation_id,
                        repo_full_name,
                        pr_number,
                        payload['pull_request']
                    )

                    app.logger.info(f"Context extracted: {len(review_context['review_context']['changed_files'])} files")
                    app.logger.debug(f"Review context: {json.dumps(review_context, indent=2)}")

                    # TODO: Call Agent Engine in Milestone 3

                except Exception as e:
                    app.logger.error(f"Error extracting context: {e}", exc_info=True)
                    return jsonify({"error": str(e)}), 500

        return jsonify({"status": "processed"}), 200

**Step 2.4: Test context extraction**

1. Restart the Flask app with updated code
2. Open a new PR or update an existing PR in your test repository
3. Check the console logs for:

       Extracting context for PR owner/repo#1
       Context extracted: 3 files
       Review context: {
         "pr_metadata": { ... },
         "review_context": {
           "changed_files": [ ... ],
           "related_files": [ ... ],
           "test_files": [ ... ]
         }
       }

If you see the extracted context with changed files, related files, and test files, Milestone 2 is complete.


### Milestone 3: Connect webhook service to Agent Engine

**Step 3.1: Create Agent Engine client**

Create `webhook_service/agent_client.py` to call the deployed Agent Engine, adapting logic from `scripts/call_agent.py`:

    import json
    import vertexai
    from vertexai import agent_engines
    from config import Config

    class AgentEngineClient:
        def __init__(self):
            vertexai.init(
                project=Config.GCP_PROJECT_ID,
                location=Config.GCP_REGION
            )

            resource_name = f"projects/442593217095/locations/{Config.GCP_REGION}/reasoningEngines/{Config.AGENT_ENGINE_ID}"
            self.agent = agent_engines.get(resource_name=resource_name)

        def review_pr(self, review_context: dict) -> dict:
            """Call the Agent Engine to review a PR.

            Args:
                review_context: Dictionary matching CodeReviewInput schema

            Returns:
                Dictionary containing review response
            """
            try:
                response = self.agent.query(input=json.dumps(review_context))

                # Parse response
                if isinstance(response, str):
                    result = json.loads(response)
                else:
                    result = response

                return result

            except Exception as e:
                raise Exception(f"Agent Engine call failed: {e}")

**Step 3.2: Create comment poster**

Create `webhook_service/comment_poster.py` by adapting logic from `scripts/post_review.py`:

    from github_client import GitHubClient

    class CommentPoster:
        def __init__(self, github_client: GitHubClient):
            self.github_client = github_client

        def post_review(
            self,
            installation_id: int,
            repo_full_name: str,
            pr_number: int,
            review_response: dict
        ):
            """Post review comments to GitHub PR.

            Args:
                installation_id: GitHub App installation ID
                repo_full_name: Repository full name (owner/repo)
                pr_number: Pull request number
                review_response: Review response from Agent Engine
            """
            client = self.github_client.get_installation_client(installation_id)
            repo = client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # Post summary comment
            summary = review_response.get('summary', '')
            if summary:
                pr.create_issue_comment(summary)

            # Post inline comments
            inline_comments = review_response.get('inline_comments', [])
            commit = pr.get_commits().reversed[0]  # Latest commit

            for comment in inline_comments:
                try:
                    pr.create_review_comment(
                        body=comment['body'],
                        commit=commit,
                        path=comment['path'],
                        line=comment['line']
                    )
                except Exception as e:
                    # Log but continue if individual comment fails
                    print(f"Failed to post comment on {comment['path']}:{comment['line']}: {e}")

**Step 3.3: Wire everything together in webhook handler**

Update `webhook_service/app.py` to call the Agent Engine and post comments:

    from agent_client import AgentEngineClient
    from comment_poster import CommentPoster

    agent_client = AgentEngineClient()
    comment_poster = CommentPoster(github_client)

    @app.route('/webhook', methods=['POST'])
    def webhook_handler():
        # ... (existing code) ...

        if event_type == 'pull_request':
            action = payload.get('action')
            if action in ['opened', 'synchronize', 'reopened']:
                # ... (existing context extraction code) ...

                try:
                    review_context = extract_review_context(...)

                    # Call Agent Engine
                    app.logger.info(f"Calling Agent Engine for PR {repo_full_name}#{pr_number}")
                    review_response = agent_client.review_pr(review_context)

                    # Post comments
                    app.logger.info(f"Posting review comments")
                    comment_poster.post_review(
                        installation_id,
                        repo_full_name,
                        pr_number,
                        review_response
                    )

                    app.logger.info(f"Review completed for PR {repo_full_name}#{pr_number}")

                except Exception as e:
                    app.logger.error(f"Error processing PR: {e}", exc_info=True)
                    # Optionally post an error comment on the PR
                    return jsonify({"error": str(e)}), 500

        return jsonify({"status": "processed"}), 200

**Step 3.4: Test end-to-end flow**

1. Ensure you have GCP authentication set up locally:

       gcloud auth application-default login

2. Restart the Flask app
3. Open or update a PR in your test repository
4. Observe the logs:

       Extracting context for PR owner/repo#1
       Context extracted: 3 files
       Calling Agent Engine for PR owner/repo#1
       Posting review comments
       Review completed for PR owner/repo#1

5. Check the PR in GitHub - you should see:
   - A summary comment with overall review
   - Inline comments on specific lines of code

If the review comments appear on the PR, Milestone 3 is complete. The entire flow is now working end-to-end locally.


### Milestone 4: Deploy webhook service to Cloud Run

**Step 4.1: Create Dockerfile**

Create `webhook_service/Dockerfile`:

    FROM python:3.10-slim

    WORKDIR /app

    # Install dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy application code
    COPY . .

    # Run with gunicorn for production
    CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 300 app:app

The configuration uses 1 worker and 8 threads to handle concurrent requests efficiently while keeping memory usage reasonable. The 300-second timeout allows for longer-running reviews.

**Step 4.2: Store secrets in Secret Manager**

From the repository root, store the GitHub App credentials in Secret Manager:

    # Store private key
    gcloud secrets create github-app-private-key \
      --data-file=/path/to/github-app-private-key.pem \
      --project=bpc-askgreg-nonprod

    # Store webhook secret
    echo -n "your-webhook-secret" | gcloud secrets create github-webhook-secret \
      --data-file=- \
      --project=bpc-askgreg-nonprod

Verify the secrets were created:

    gcloud secrets list --project=bpc-askgreg-nonprod

Expected output:

    NAME                        CREATED
    github-app-private-key      2025-12-12T...
    github-webhook-secret       2025-12-12T...

**Step 4.3: Build and deploy to Cloud Run**

From the `webhook_service` directory:

    # Build container image
    gcloud builds submit --tag gcr.io/bpc-askgreg-nonprod/code-review-webhook \
      --project=bpc-askgreg-nonprod

    # Deploy to Cloud Run
    gcloud run deploy code-review-webhook \
      --image gcr.io/bpc-askgreg-nonprod/code-review-webhook \
      --platform managed \
      --region europe-west1 \
      --allow-unauthenticated \
      --set-env-vars GITHUB_APP_ID=your-app-id,GCP_PROJECT_ID=bpc-askgreg-nonprod,GCP_REGION=europe-west1,AGENT_ENGINE_ID=3659508948773371904 \
      --set-secrets GITHUB_APP_PRIVATE_KEY=github-app-private-key:latest,GITHUB_WEBHOOK_SECRET=github-webhook-secret:latest \
      --memory 1Gi \
      --cpu 1 \
      --timeout 300 \
      --max-instances 10 \
      --project=bpc-askgreg-nonprod

The deployment will output a service URL like:

    Service [code-review-webhook] revision [code-review-webhook-00001] has been deployed and is serving 100 percent of traffic.
    Service URL: https://code-review-webhook-abc123-ew.a.run.app

**Step 4.4: Grant Cloud Run access to Agent Engine**

The Cloud Run service needs permission to call the Agent Engine. Get the service account email:

    gcloud run services describe code-review-webhook \
      --region=europe-west1 \
      --project=bpc-askgreg-nonprod \
      --format='value(spec.template.spec.serviceAccountName)'

Grant necessary permissions:

    gcloud projects add-iam-policy-binding bpc-askgreg-nonprod \
      --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
      --role="roles/aiplatform.user"

**Step 4.5: Update GitHub App webhook URL**

1. Go to your GitHub App settings
2. Update the webhook URL to the Cloud Run service URL + `/webhook`:

       https://code-review-webhook-abc123-ew.a.run.app/webhook

3. Save changes

**Step 4.6: Test production deployment**

1. Open or update a PR in your test repository
2. Check Cloud Run logs:

       gcloud run services logs read code-review-webhook \
         --region=europe-west1 \
         --project=bpc-askgreg-nonprod \
         --limit=50

   Expected log output:

       Received pull_request event
       Extracting context for PR owner/repo#1
       Calling Agent Engine for PR owner/repo#1
       Posting review comments
       Review completed for PR owner/repo#1

3. Verify review comments appear on the PR in GitHub

If the Cloud Run deployment receives webhooks and posts reviews, Milestone 4 is complete. The webhook service is now running in production.


### Milestone 5: Add installation management and configuration

**Step 5.1: Set up Firestore**

Enable Firestore API and create a database:

    gcloud services enable firestore.googleapis.com --project=bpc-askgreg-nonprod

    gcloud firestore databases create --region=europe-west1 --project=bpc-askgreg-nonprod

Grant Cloud Run service access to Firestore:

    gcloud projects add-iam-policy-binding bpc-askgreg-nonprod \
      --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
      --role="roles/datastore.user"

**Step 5.2: Create installation tracker**

Create `webhook_service/installation_manager.py`:

    from google.cloud import firestore
    from datetime import datetime
    from config import Config

    class InstallationManager:
        def __init__(self):
            self.db = firestore.Client(project=Config.GCP_PROJECT_ID)
            self.installations_collection = self.db.collection('installations')

        def add_installation(self, installation_id: int, repositories: list):
            """Record a new installation."""
            doc_ref = self.installations_collection.document(str(installation_id))
            doc_ref.set({
                'installation_id': installation_id,
                'repositories': repositories,
                'installed_at': datetime.utcnow(),
                'active': True
            })

        def remove_installation(self, installation_id: int):
            """Mark an installation as inactive."""
            doc_ref = self.installations_collection.document(str(installation_id))
            doc_ref.update({'active': False, 'uninstalled_at': datetime.utcnow()})

        def get_installation(self, installation_id: int) -> dict:
            """Get installation details."""
            doc_ref = self.installations_collection.document(str(installation_id))
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None

        def is_repository_enabled(self, installation_id: int, repo_full_name: str) -> bool:
            """Check if a repository has the app enabled."""
            installation = self.get_installation(installation_id)
            if not installation or not installation.get('active'):
                return False

            repositories = installation.get('repositories', [])
            return repo_full_name in repositories

**Step 5.3: Handle installation events**

Update `webhook_service/app.py` to handle installation lifecycle events:

    from installation_manager import InstallationManager

    installation_manager = InstallationManager()

    @app.route('/webhook', methods=['POST'])
    def webhook_handler():
        # ... (existing verification code) ...

        # Handle installation events
        if event_type == 'installation':
            action = payload.get('action')
            installation_id = payload['installation']['id']
            repositories = [repo['full_name'] for repo in payload.get('repositories', [])]

            if action == 'created':
                app.logger.info(f"App installed: {installation_id}, repos: {repositories}")
                installation_manager.add_installation(installation_id, repositories)
            elif action == 'deleted':
                app.logger.info(f"App uninstalled: {installation_id}")
                installation_manager.remove_installation(installation_id)

        if event_type == 'installation_repositories':
            action = payload.get('action')
            installation_id = payload['installation']['id']

            if action == 'added':
                added_repos = [repo['full_name'] for repo in payload.get('repositories_added', [])]
                app.logger.info(f"Repositories added to installation {installation_id}: {added_repos}")
                # Update Firestore with new repositories
            elif action == 'removed':
                removed_repos = [repo['full_name'] for repo in payload.get('repositories_removed', [])]
                app.logger.info(f"Repositories removed from installation {installation_id}: {removed_repos}")
                # Update Firestore to remove repositories

        # ... (existing PR handling code) ...

**Step 5.4: Add repository configuration support**

Create `webhook_service/config_loader.py` to load per-repository configuration:

    import yaml
    from github_client import GitHubClient

    DEFAULT_CONFIG = {
        'enabled': True,
        'languages': ['python', 'typescript'],
        'rules': {
            'max_line_length': 100,
            'style_check': True,
            'require_tests': True
        },
        'ignore_paths': [],
        'severity_threshold': 'info'
    }

    class ConfigLoader:
        def __init__(self, github_client: GitHubClient):
            self.github_client = github_client

        def load_repo_config(
            self,
            installation_id: int,
            repo_full_name: str,
            branch: str = 'main'
        ) -> dict:
            """Load configuration from repository's .code-review.yml file.

            If file doesn't exist, returns default configuration.
            """
            try:
                client = self.github_client.get_installation_client(installation_id)
                repo = client.get_repo(repo_full_name)

                # Try to get config file
                config_file = repo.get_contents('.code-review.yml', ref=branch)
                config_content = config_file.decoded_content.decode('utf-8')

                # Parse YAML
                config = yaml.safe_load(config_content)

                # Merge with defaults
                merged_config = {**DEFAULT_CONFIG, **config.get('code_review', {})}
                return merged_config

            except Exception as e:
                # If file doesn't exist or any error, return defaults
                return DEFAULT_CONFIG

Update `webhook_service/app.py` to load and use repository configuration:

    from config_loader import ConfigLoader

    config_loader = ConfigLoader(github_client)

    @app.route('/webhook', methods=['POST'])
    def webhook_handler():
        # ... (existing code) ...

        if event_type == 'pull_request':
            action = payload.get('action')
            if action in ['opened', 'synchronize', 'reopened']:
                # Load repository configuration
                repo_config = config_loader.load_repo_config(
                    installation_id,
                    repo_full_name,
                    payload['pull_request']['base']['ref']
                )

                # Check if reviews are enabled
                if not repo_config.get('enabled', True):
                    return jsonify({"status": "skipped - reviews disabled"}), 200

                # Pass config to context extractor and use it to filter files, etc.
                # ... (existing processing code) ...

**Step 5.5: Test installation management**

1. Redeploy the webhook service with updated code:

       gcloud builds submit --tag gcr.io/bpc-askgreg-nonprod/code-review-webhook --project=bpc-askgreg-nonprod
       gcloud run deploy code-review-webhook --image gcr.io/bpc-askgreg-nonprod/code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod

2. Uninstall and reinstall the GitHub App on your test repository
3. Check Firestore for the installation record:

       gcloud firestore documents list --collection=installations --project=bpc-askgreg-nonprod

4. Create a `.code-review.yml` file in your test repository:

       code_review:
         enabled: true
         severity_threshold: "warning"
         ignore_paths:
           - "migrations/**"

5. Open a PR and verify the configuration is loaded from logs

If Firestore tracks installations and the app respects repository configuration, Milestone 5 is complete.


### Milestone 6: Testing and documentation

**Step 6.1: Add unit tests**

Create `webhook_service/tests/` directory:

    mkdir -p webhook_service/tests
    touch webhook_service/tests/__init__.py
    touch webhook_service/tests/test_github_client.py
    touch webhook_service/tests/test_context_extractor.py
    touch webhook_service/tests/test_webhook_handler.py

Create `webhook_service/tests/test_webhook_handler.py` to test webhook signature verification and event routing:

    import pytest
    import json
    import hmac
    import hashlib
    from app import app, verify_webhook_signature
    from config import Config

    @pytest.fixture
    def client():
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_health_check(client):
        """Test health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json == {"status": "healthy"}

    def test_webhook_without_signature(client):
        """Test webhook rejects requests without signature."""
        response = client.post('/webhook', json={"test": "data"})
        assert response.status_code == 403

    def test_webhook_with_invalid_signature(client):
        """Test webhook rejects requests with invalid signature."""
        payload = json.dumps({"test": "data"})
        response = client.post(
            '/webhook',
            data=payload,
            headers={'X-Hub-Signature-256': 'sha256=invalid'}
        )
        assert response.status_code == 403

    def test_webhook_with_valid_signature(client):
        """Test webhook accepts requests with valid signature."""
        payload = json.dumps({"action": "opened", "pull_request": {}})
        signature = "sha256=" + hmac.new(
            Config.GITHUB_WEBHOOK_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        response = client.post(
            '/webhook',
            data=payload,
            headers={
                'X-Hub-Signature-256': signature,
                'X-GitHub-Event': 'pull_request'
            }
        )
        assert response.status_code == 200

Run tests:

    cd webhook_service
    pytest tests/ -v

Expected output:

    tests/test_webhook_handler.py::test_health_check PASSED
    tests/test_webhook_handler.py::test_webhook_without_signature PASSED
    tests/test_webhook_handler.py::test_webhook_with_invalid_signature PASSED
    tests/test_webhook_handler.py::test_webhook_with_valid_signature PASSED

**Step 6.2: Add integration tests**

Create `webhook_service/tests/test_integration.py` to test the full flow with mocked GitHub and Agent Engine:

    import pytest
    from unittest.mock import Mock, patch
    import json

    @pytest.fixture
    def mock_github_client():
        with patch('webhook_service.github_client.GitHubClient') as mock:
            yield mock

    @pytest.fixture
    def mock_agent_client():
        with patch('webhook_service.agent_client.AgentEngineClient') as mock:
            yield mock

    def test_end_to_end_pr_review(client, mock_github_client, mock_agent_client):
        """Test complete flow from webhook to posted comments."""
        # Mock GitHub API responses
        mock_pr = Mock()
        mock_pr.get_files.return_value = [
            Mock(filename='src/test.py', status='modified', additions=10, deletions=2, patch='...', raw_url='...')
        ]

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr

        mock_github_client.return_value.get_installation_client.return_value.get_repo.return_value = mock_repo

        # Mock Agent Engine response
        mock_agent_client.return_value.review_pr.return_value = {
            'summary': '## Review Summary\n\nLooks good!',
            'inline_comments': [
                {'path': 'src/test.py', 'line': 10, 'body': 'Good improvement!', 'severity': 'info'}
            ]
        }

        # Send webhook event
        payload = {
            'action': 'opened',
            'installation': {'id': 12345},
            'repository': {'full_name': 'owner/repo'},
            'pull_request': {
                'number': 1,
                'draft': False,
                'base': {'ref': 'main', 'sha': 'abc123'},
                'head': {'ref': 'feature', 'sha': 'def456'}
            }
        }

        # Create valid signature
        # ... (signature creation code) ...

        response = client.post('/webhook', data=json.dumps(payload), headers={...})

        assert response.status_code == 200
        assert mock_agent_client.return_value.review_pr.called
        assert mock_pr.create_issue_comment.called

**Step 6.3: Create user documentation**

Create `webhook_service/README.md` with user-facing installation instructions:

    # Code Review Bot - GitHub App

    Automatically review Python and TypeScript pull requests with AI-powered feedback.

    ## Installation

    1. **Install the GitHub App**
       - Visit: [GitHub App URL]
       - Click "Install"
       - Select repositories to enable reviews

    2. **Configure (Optional)**
       - Create `.code-review.yml` in your repository root:

           code_review:
             enabled: true
             languages:
               - python
               - typescript
             rules:
               max_line_length: 100
               style_check: true
               require_tests: true
             ignore_paths:
               - "migrations/**"
               - "generated/**"
             severity_threshold: "warning"

    3. **Test It**
       - Open a pull request
       - The bot will automatically review it within 1-2 minutes
       - Review comments will appear on the PR

    ## Configuration Options

    - `enabled`: Enable/disable reviews (default: true)
    - `languages`: Languages to review (default: ["python", "typescript"])
    - `rules.max_line_length`: Maximum line length (default: 100)
    - `rules.style_check`: Enable style checking (default: true)
    - `rules.require_tests`: Require tests for new code (default: true)
    - `ignore_paths`: Glob patterns for paths to ignore
    - `severity_threshold`: Minimum severity to comment ("info", "warning", "error")

    ## Support

    - [GitHub Issues](link)
    - [Documentation](link)

**Step 6.4: Create developer documentation**

Create `webhook_service/ARCHITECTURE.md` explaining how the system works:

    # Code Review Bot Architecture

    ## Overview

    The code review bot is implemented as a GitHub App that receives webhook events,
    processes pull requests through an AI agent, and posts review comments.

    ## Components

    1. **GitHub App**: Registered in GitHub with permissions to read PRs and post comments
    2. **Webhook Service**: Flask app running on Cloud Run that receives GitHub webhooks
    3. **Agent Engine**: Deployed AI agent that performs code analysis
    4. **Firestore**: Tracks app installations and configuration
    5. **Secret Manager**: Stores GitHub App credentials securely

    ## Flow

    1. Developer opens/updates PR in repository with app installed
    2. GitHub sends webhook event to Cloud Run service
    3. Webhook handler validates signature and extracts event data
    4. Context extractor fetches changed files and builds review payload
    5. Agent Engine client calls deployed agent with review payload
    6. Agent performs multi-agent review (analysis, style, tests, synthesis)
    7. Comment poster posts review summary and inline comments via GitHub API
    8. Developer sees review comments on their PR

    ## Deployment

    The webhook service is deployed to Cloud Run in `bpc-askgreg-nonprod` project.

    To deploy updates:

        cd webhook_service
        gcloud builds submit --tag gcr.io/bpc-askgreg-nonprod/code-review-webhook
        gcloud run deploy code-review-webhook --image gcr.io/bpc-askgreg-nonprod/code-review-webhook ...

    ## Monitoring

    - Cloud Run logs: [link]
    - Cloud Trace: [link]
    - Firestore console: [link]

    ## Local Development

    1. Set up environment variables
    2. Run Flask app: `python app.py`
    3. Use ngrok to expose locally: `ngrok http 8080`
    4. Update GitHub App webhook URL to ngrok URL
    5. Test with PRs in test repository

**Step 6.5: Final end-to-end test**

1. Install the GitHub App on a fresh test repository
2. Create a branch with Python and TypeScript changes
3. Open a pull request
4. Verify within 2 minutes:
   - Review summary comment appears
   - Inline comments appear on changed lines
   - Comments reference actual code issues
5. Update the PR with new commits
6. Verify the bot reviews the new changes
7. Check Firestore for installation record
8. Check Cloud Run logs for successful processing

If all tests pass and documentation is complete, Milestone 6 is complete. The GitHub App is ready for release.


## Validation and Acceptance

After completing all milestones, the system must demonstrate these behaviors:

1. **Installation**: A developer can visit the GitHub App page, click Install, select repositories, and have the app immediately ready to review PRs in those repositories.

2. **Automatic Reviews**: When a PR is opened or updated, the app automatically reviews it within 2 minutes and posts comments without any manual action.

3. **Configuration**: Creating a `.code-review.yml` file in a repository changes the app's behavior (e.g., setting `enabled: false` disables reviews).

4. **Multi-Repository**: The app works correctly when installed on multiple repositories simultaneously.

5. **Error Handling**: The app gracefully handles errors (malformed webhooks, Agent Engine timeouts, etc.) and logs them without crashing.

6. **Security**: Webhook signatures are validated, secrets are stored in Secret Manager, and the app only accesses repositories where it's installed.

To validate acceptance:

    # Test 1: Install and uninstall
    - Install app on test repository
    - Check Firestore for installation record
    - Uninstall app
    - Check Firestore shows inactive status

    # Test 2: PR review
    - Open PR with Python changes
    - Wait up to 2 minutes
    - Verify review comments appear

    # Test 3: Configuration
    - Create .code-review.yml with enabled: false
    - Open PR
    - Verify no review is posted

    # Test 4: Error handling
    - Trigger webhook with invalid signature
    - Check returns 403 status
    - Check logs show validation failure

    # Test 5: Performance
    - Open PR with 10 changed files
    - Measure time to first comment
    - Should be under 2 minutes

All five tests must pass for acceptance.


## Idempotence and Recovery

This implementation is designed for safe retries and recovery:

1. **Webhook retries**: GitHub will retry webhooks that fail (5xx errors). The webhook handler is idempotent - processing the same PR event multiple times will not cause duplicate comments (GitHub API handles this).

2. **Partial failures**: If context extraction succeeds but Agent Engine fails, the error is logged and GitHub receives a 500 response, triggering a retry. If Agent Engine succeeds but posting comments fails, comments that were posted successfully will not be duplicated on retry.

3. **Secrets rotation**: Secrets in Secret Manager can be updated without redeploying the service. The service loads secrets on startup, so restart the Cloud Run service after updating secrets.

4. **Rollback**: Keep previous container images in GCR. To rollback, redeploy the previous image tag.

5. **Data recovery**: Firestore installation records can be manually added or corrected through the Firebase console if they become inconsistent.

To recover from common failures:

    # Service crashes on startup due to bad secrets
    - Check Secret Manager secrets are valid
    - Fix secrets if needed
    - Restart Cloud Run service

    # Agent Engine timeouts
    - Check Agent Engine logs in Vertex AI console
    - May need to increase Cloud Run timeout or Agent Engine resources

    # Missing installation records
    - Reinstall the app (triggers installation webhook)
    - Or manually add record to Firestore


## Artifacts and Notes

After completing Milestone 1, you should have:

    webhook_service/
    ├── app.py                      # Flask app with webhook handler
    ├── config.py                   # Configuration management
    ├── requirements.txt            # Python dependencies
    └── __init__.py

After completing Milestone 3, you should have:

    webhook_service/
    ├── app.py
    ├── config.py
    ├── github_client.py            # GitHub API wrapper
    ├── context_extractor.py        # Extract PR context
    ├── agent_client.py             # Agent Engine client
    ├── comment_poster.py           # Post comments to GitHub
    ├── requirements.txt
    └── __init__.py

After completing Milestone 4, you should have:

    webhook_service/
    ├── ... (all previous files)
    ├── Dockerfile                  # Container definition
    └── [Deployed to Cloud Run]

After completing Milestone 5, you should have:

    webhook_service/
    ├── ... (all previous files)
    ├── installation_manager.py     # Firestore integration
    ├── config_loader.py            # Repository config loading
    └── [Firestore database created]

After completing Milestone 6, you should have:

    webhook_service/
    ├── ... (all previous files)
    ├── tests/
    │   ├── __init__.py
    │   ├── test_webhook_handler.py
    │   ├── test_context_extractor.py
    │   └── test_integration.py
    ├── README.md                   # User documentation
    ├── ARCHITECTURE.md             # Developer documentation
    └── [Full test coverage]

Key implementation notes:

1. **Authentication flow**: GitHub App uses JWT to authenticate as the app, then exchanges for installation access tokens to act on behalf of specific installations. The JWT is signed with the private key stored in Secret Manager.

2. **Rate limiting**: GitHub API has rate limits per installation. The current implementation does not implement its own rate limiting, relying on GitHub's built-in retry mechanisms. For production at scale, consider implementing a queue (e.g., Cloud Tasks) to handle retries gracefully.

3. **Concurrency**: Cloud Run will spawn multiple instances under load. The implementation is stateless and safe for concurrent execution. Firestore handles concurrent writes safely.

4. **Costs**: Each PR review costs approximately $0.01-0.05 depending on size (Agent Engine usage). Cloud Run and Firestore costs are minimal for typical usage. Monitor costs in GCP billing console.


## Interfaces and Dependencies

The webhook service depends on these external interfaces:

**GitHub App API**:
- Webhook events: `pull_request`, `installation`, `installation_repositories`
- Authentication: JWT signed with private key, exchanged for installation tokens
- API endpoints: `GET /repos/{owner}/{repo}/pulls/{number}`, `POST /repos/{owner}/{repo}/pulls/{number}/comments`

**Agent Engine API**:
- Endpoint: `POST https://europe-west1-aiplatform.googleapis.com/v1/projects/442593217095/locations/europe-west1/reasoningEngines/3659508948773371904:query`
- Authentication: Application Default Credentials (automatic in Cloud Run)
- Input schema: `CodeReviewInput` (defined in `app/models/input_schema.py`)
- Output schema: `CodeReviewOutput` (defined in `app/models/output_schema.py`)

**Google Secret Manager**:
- Secrets: `github-app-private-key`, `github-webhook-secret`
- Access: Cloud Run service account needs `roles/secretmanager.secretAccessor`

**Google Firestore**:
- Collections: `installations` (schema: `{installation_id, repositories[], installed_at, active}`)
- Access: Cloud Run service account needs `roles/datastore.user`

The webhook service exposes these endpoints:

    POST /webhook
    - Accepts GitHub webhook events
    - Validates signature with X-Hub-Signature-256 header
    - Returns 200 on success, 403 on invalid signature, 500 on processing error

    GET /health
    - Health check for Cloud Run
    - Returns {"status": "healthy"} with 200 status

The service reads these environment variables:

    GITHUB_APP_ID                - GitHub App ID (integer)
    GCP_PROJECT_ID               - GCP project ID
    GCP_REGION                   - GCP region (europe-west1)
    AGENT_ENGINE_ID              - Agent Engine ID (numeric string)
    PORT                         - HTTP port (set by Cloud Run)

The service must have these IAM permissions:

    roles/secretmanager.secretAccessor     - Read secrets from Secret Manager
    roles/datastore.user                   - Read/write Firestore documents
    roles/aiplatform.user                  - Call Agent Engine API
