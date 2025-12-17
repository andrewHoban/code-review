# GitHub App Implementation - DEPRECATED ⚠️

## Status: Deprecated

**This GitHub App/webhook approach is no longer used.** The project now uses GitHub Actions workflows instead, which is simpler and doesn't require infrastructure setup.

See [Team Adoption Guide](docs/TEAM_ADOPTION_GUIDE.md) for the current approach.

## Summary (Historical)

I've successfully implemented all 6 milestones from the GitHub App plan. The webhook service is now deprecated in favor of GitHub Actions.

## What Was Built

### Core Service Files

All files are in the `webhook_service/` directory:

1. **`app.py`** - Main Flask application with webhook handler
2. **`config.py`** - Configuration management with Secret Manager support
3. **`github_client.py`** - GitHub API client using App authentication
4. **`context_extractor.py`** - Extract PR context from GitHub API
5. **`agent_client.py`** - Client for calling Agent Engine
6. **`comment_poster.py`** - Post review comments to GitHub PRs
7. **`installation_manager.py`** - Track installations in Firestore
8. **`config_loader.py`** - Load repository-specific configuration
9. **`Dockerfile`** - Container image for Cloud Run
10. **`requirements.txt`** - Python dependencies
11. **`tests/test_webhook_handler.py`** - Basic test suite

### Features Implemented

✅ Webhook signature validation
✅ PR context extraction from GitHub API
✅ Agent Engine integration with streaming support
✅ Automatic comment posting to GitHub PRs
✅ Installation tracking in Firestore
✅ Repository configuration via `.code-review.yml`
✅ Health check endpoint
✅ Error handling and logging

## Next Steps (Manual Actions Required)

### 1. Create GitHub App

You need to create the GitHub App manually in GitHub's UI:

1. Go to: https://github.com/settings/apps/new
2. Configure:
   - **GitHub App name**: `code-review-bot-{yourname}` (must be unique)
   - **Homepage URL**: Your repository URL
   - **Webhook**:
     - **Uncheck "Active"** (you'll enable this after deployment)
     - **Webhook URL**: Leave empty for now
     - **Webhook secret**: Generate a secure random string with `openssl rand -hex 32` (save it securely - you'll need it for Step 2!)
   - **Permissions**:
     - Repository permissions:
       - Pull requests: **Read & write**
       - Contents: **Read-only**
       - Metadata: **Read-only** (automatic)
   - **Subscribe to events**:
     - ✅ Pull request
     - ✅ Installation
     - ✅ Installation repositories
   - **Where can this GitHub App be installed?**: Choose based on your needs
3. Click **Create GitHub App**
4. On the app page:
   - **Generate a private key** and download it (save as `github-app-private-key.pem`)
   - **Note the App ID** (you'll need this)

### 2. Store Secrets in Google Secret Manager

```bash
# Store GitHub App private key
gcloud secrets create github-app-private-key \
  --data-file=/path/to/github-app-private-key.pem \
  --project=bpc-askgreg-nonprod

# Store webhook secret (use the secret you generated in Step 1)
echo -n "your-webhook-secret-from-step-1" | \
  gcloud secrets create github-webhook-secret \
  --data-file=- \
  --project=bpc-askgreg-nonprod
```

### 3. Grant Cloud Run Access to Secrets

After deploying, grant the Cloud Run service account access:

```bash
# Get service account email
SA=$(gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(spec.template.spec.serviceAccountName)')

# Grant secret access
gcloud secrets add-iam-policy-binding github-app-private-key \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=bpc-askgreg-nonprod

gcloud secrets add-iam-policy-binding github-webhook-secret \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=bpc-askgreg-nonprod
```

### 4. Deploy Webhook Service

```bash
# Set GitHub App ID
export GITHUB_APP_ID="your-app-id-from-step-1"

# Deploy
make deploy-webhook

# Or deploy manually:
cd webhook_service
gcloud builds submit --tag gcr.io/bpc-askgreg-nonprod/code-review-webhook --project=bpc-askgreg-nonprod
gcloud run deploy code-review-webhook \
  --image gcr.io/bpc-askgreg-nonprod/code-review-webhook \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars GITHUB_APP_ID=${GITHUB_APP_ID},GCP_PROJECT_ID=bpc-askgreg-nonprod,GCP_REGION=europe-west1,AGENT_ENGINE_ID=3659508948773371904 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --project=bpc-askgreg-nonprod
```

### 5. Get Service URL and Enable Webhook

```bash
# Get service URL
gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(status.url)'
```

Then:
1. Go to your GitHub App settings
2. In the **Webhook** section:
   - **Check "Active"** to enable webhooks
   - Set **Webhook URL** to: `{service-url}/webhook`
3. Save changes

### 6. Install and Test

1. Go to your GitHub App page
2. Click **Install App**
3. Select a test repository
4. Open or update a PR
5. Check Cloud Run logs: `make logs-webhook`
6. Verify review comments appear on the PR!

## Testing Locally (Before Deployment)

```bash
# Set environment variables
export GITHUB_APP_ID="your-app-id"
export GITHUB_WEBHOOK_SECRET="your-webhook-secret"
export GCP_PROJECT_ID="bpc-askgreg-nonprod"

# Install dependencies
cd webhook_service
pip install -r requirements.txt

# Run locally
python app.py

# In another terminal, expose with ngrok
ngrok http 8080

# Update GitHub App webhook URL to ngrok URL + /webhook
# Test with a PR!
```

## File Structure

```
webhook_service/
├── __init__.py
├── app.py                    # Main Flask app
├── config.py                 # Configuration
├── github_client.py          # GitHub API client
├── context_extractor.py      # PR context extraction
├── agent_client.py           # Agent Engine client
├── comment_poster.py         # Post comments
├── installation_manager.py   # Firestore tracking
├── config_loader.py          # Repository config
├── requirements.txt          # Dependencies
├── Dockerfile               # Container image
├── README.md                # Documentation
├── .gitignore
└── tests/
    ├── __init__.py
    └── test_webhook_handler.py
```

## Architecture

```
GitHub PR Event
    ↓
Webhook Service (Cloud Run)
    ├─ Validate signature
    ├─ Extract PR context
    ├─ Load repo config (.code-review.yml)
    ├─ Call Agent Engine
    └─ Post comments to GitHub
```

## Configuration

### Repository Configuration

Create `.code-review.yml` in your repository:

```yaml
code_review:
  enabled: true
  languages: [python, typescript]
  rules:
    max_line_length: 100
    style_check: true
    require_tests: true
  ignore_paths:
    - "migrations/**"
  severity_threshold: "warning"
```

## Monitoring

```bash
# View logs
make logs-webhook

# Stream logs
make tail-webhook

# Check status
make status-webhook

# Health check
curl $(gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(status.url)')/health
```

## Troubleshooting

### Webhook not receiving events
- Verify webhook URL in GitHub App matches Cloud Run URL + `/webhook`
- Check webhook secret matches in both places
- View Cloud Run logs for errors

### Agent Engine timeout
- Large PRs may timeout (default 5 minutes)
- Check Agent Engine logs in GCP Console
- Consider increasing Cloud Run timeout

### Permission errors
- Ensure Cloud Run service account has `roles/aiplatform.user`
- Ensure service account can access Secret Manager
- Verify GitHub App permissions

## Documentation

- [Webhook Service README](webhook_service/README.md)
- [GitHub App Plan](GITHUB_APP_PLAN.md)
- [Deployment Guide](WEBHOOK_DEPLOYMENT.md)

## Success Criteria

✅ All 6 milestones completed
✅ Webhook service code implemented
✅ Docker container ready
✅ Tests created
✅ Documentation written
✅ Ready for deployment

**Next**: Follow the "Next Steps" section above to deploy and test!
