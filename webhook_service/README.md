# Webhook Service for GitHub App

This service receives webhook events from GitHub and orchestrates code reviews using the deployed Agent Engine.

## Architecture

```
GitHub PR Event
    ↓
Webhook Service (this service)
    ↓
1. Validate webhook signature
2. Extract PR context (files, diffs, metadata)
3. Call Agent Engine
4. Post review comments to GitHub
```

## Setup

### 1. Create GitHub App

1. Go to GitHub Settings → Developer settings → GitHub Apps → New GitHub App
2. Configure:
   - **Name**: `code-review-bot-{yourname}` (must be unique)
   - **Webhook URL**: Leave blank for now (add after deployment)
   - **Webhook secret**: Generate a random string (save securely)
   - **Permissions**:
     - Pull requests: Read & write
     - Contents: Read-only
     - Metadata: Read-only
   - **Subscribe to events**: Pull request, Installation, Installation repositories
3. Generate and download private key
4. Note the App ID

### 2. Store Secrets in Google Secret Manager

```bash
# Store private key
gcloud secrets create github-app-private-key \
  --data-file=/path/to/github-app-private-key.pem \
  --project=bpc-askgreg-nonprod

# Store webhook secret
echo -n "your-webhook-secret" | gcloud secrets create github-webhook-secret \
  --data-file=- \
  --project=bpc-askgreg-nonprod
```

### 3. Deploy to Cloud Run

```bash
# From repository root
export GITHUB_APP_ID="your-app-id"
make deploy-webhook
```

Or use automated deployment via GitHub Actions (push to main).

## Local Development

### Run Locally

```bash
# Set environment variables
export GITHUB_APP_ID="your-app-id"
export GITHUB_WEBHOOK_SECRET="your-webhook-secret"
export GCP_PROJECT_ID="bpc-askgreg-nonprod"

# Install dependencies
pip install -r requirements.txt

# Run Flask app
python app.py
```

### Test with ngrok

```bash
# In another terminal
ngrok http 8080

# Update GitHub App webhook URL to ngrok URL + /webhook
# Example: https://abc123.ngrok.io/webhook
```

## Configuration

### Repository Configuration

Create `.code-review.yml` in your repository root:

```yaml
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
```

## Testing

### Run All Tests

```bash
cd webhook_service
pip install -r requirements.txt
pytest tests/ -v
```

### Test Coverage

The test suite includes:

- **Unit Tests** (`test_webhook_handler.py`, `test_github_client.py`, etc.)
  - Webhook signature validation
  - GitHub client functionality
  - Context extraction
  - Agent Engine client
  - Comment posting

- **Integration Tests** (`test_integration.py`)
  - End-to-end webhook processing
  - Installation event handling
  - Draft PR skipping

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/ -m unit -v

# Integration tests only
pytest tests/ -m integration -v

# Specific test file
pytest tests/test_webhook_handler.py -v
```

## Testing

### Run All Tests

```bash
cd webhook_service
pip install -r requirements.txt
pytest tests/ -v
```

### Test Coverage

The test suite includes:

- **Unit Tests**:
  - `test_webhook_handler.py` - Webhook signature validation and routing
  - `test_github_client.py` - GitHub API client functionality
  - `test_context_extractor.py` - PR context extraction
  - `test_agent_client.py` - Agent Engine client
  - `test_comment_poster.py` - Comment posting to GitHub

- **Integration Tests** (`test_integration.py`):
  - End-to-end webhook processing flow
  - Installation event handling
  - Draft PR skipping

See [TEST_SUMMARY.md](TEST_SUMMARY.md) for detailed test documentation.

## Monitoring

```bash
# View logs
make logs-webhook

# Stream logs
make tail-webhook

# Check status
make status-webhook
```

## Troubleshooting

### Webhook not receiving events
- Check GitHub App webhook URL matches Cloud Run service URL + `/webhook`
- Verify webhook secret matches in both GitHub App and Secret Manager
- Check Cloud Run logs for errors

### Agent Engine timeout
- Large PRs may timeout (default: 5 minutes)
- Check Agent Engine logs in GCP Console
- Consider increasing timeout in Cloud Run deployment

### Permission errors
- Ensure Cloud Run service account has `roles/aiplatform.user`
- Ensure service account can access Secret Manager secrets
- Check GitHub App permissions are correct

## Files

- `app.py` - Main Flask application
- `config.py` - Configuration management
- `github_client.py` - GitHub API client
- `context_extractor.py` - Extract PR context
- `agent_client.py` - Agent Engine client
- `comment_poster.py` - Post comments to GitHub
- `installation_manager.py` - Track installations in Firestore
- `config_loader.py` - Load repository configuration
- `Dockerfile` - Container image definition
- `requirements.txt` - Python dependencies
