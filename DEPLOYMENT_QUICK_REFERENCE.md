# Deployment Quick Reference

This is a quick reference for deploying and managing the code review bot. For detailed instructions, see `WEBHOOK_DEPLOYMENT.md`.

## Two Services to Manage

| Service | What it does | Deploy command | When to update |
|---------|-------------|----------------|----------------|
| **Agent Engine** | AI code review logic | `make deploy` | Changed review prompts, analysis logic, or agent pipelines |
| **Webhook Service** | GitHub webhook handling | `make deploy-webhook` | Changed webhook processing, GitHub API integration, or configuration |

## Common Commands

### Deploy

```bash
# Deploy Agent Engine (review logic)
make deploy

# Deploy Webhook Service (GitHub integration)
export GITHUB_APP_ID="your-app-id"
make deploy-webhook
```

### Monitor

```bash
# Check webhook service status
make status-webhook

# View recent logs
make logs-webhook

# Stream logs (real-time)
make tail-webhook

# Check health
curl $(gcloud run services describe code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod --format='value(status.url)')/health
```

### Test Locally

```bash
# Test webhook service locally
export GITHUB_APP_ID="your-app-id"
export GITHUB_WEBHOOK_SECRET="your-webhook-secret"
make run-webhook

# In another terminal
ngrok http 8080
```

### Rollback

```bash
# List webhook service revisions
gcloud run revisions list --service=code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod

# Rollback to specific revision
gcloud run services update-traffic code-review-webhook --to-revisions=REVISION_NAME=100 --region=europe-west1 --project=bpc-askgreg-nonprod

# Rollback Agent Engine (redeploy previous commit)
git checkout PREVIOUS_COMMIT
make deploy
git checkout main
```

## Daily Workflow

### Scenario 1: Update Review Logic

```bash
# Make changes to agent code
vim app/agents/python_review_pipeline.py

# Test
make test

# Deploy
make deploy

# Webhook service automatically uses updated agent
```

### Scenario 2: Update Webhook Handling

```bash
# Make changes to webhook service
vim webhook_service/app.py

# Test locally
make run-webhook

# Commit and push (auto-deploys)
git add webhook_service/
git commit -m "fix: improve error handling"
git push origin main
```

### Scenario 3: Update Both

```bash
# Update agent logic
vim app/agents/python_review_pipeline.py

# Update webhook handling
vim webhook_service/app.py

# Deploy agent first
make test
make deploy

# Deploy webhook service
export GITHUB_APP_ID="your-app-id"
make deploy-webhook
```

## Troubleshooting

### Webhook service not receiving events

```bash
# Check service is running
make status-webhook

# Check recent logs for errors
make logs-webhook

# Verify GitHub App webhook URL
gcloud run services describe code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod --format='value(status.url)'
# Should match GitHub App settings + "/webhook"
```

### Agent Engine timeout

```bash
# Check Agent Engine logs
gcloud ai reasoning-engines query 3659508948773371904 --region=europe-west1 --project=bpc-askgreg-nonprod

# May need to increase timeout
gcloud run services update code-review-webhook --timeout=600 --region=europe-west1 --project=bpc-askgreg-nonprod
```

### Permission errors

```bash
# Grant webhook service access to Agent Engine
SA=$(gcloud run services describe code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod --format='value(spec.template.spec.serviceAccountName)')

gcloud projects add-iam-policy-binding bpc-askgreg-nonprod --member="serviceAccount:${SA}" --role="roles/aiplatform.user"
```

## Required Secrets

### GitHub Repository Secrets

```bash
# Add to GitHub repository
gh secret set GITHUB_APP_ID -b"your-app-id"
gh secret set GCP_PROJECT_ID -b"bpc-askgreg-nonprod"
gh secret set GCP_PROJECT_NUMBER -b"442593217095"
gh secret set GCP_REGION -b"europe-west1"
```

### Google Secret Manager

```bash
# GitHub App private key
gcloud secrets create github-app-private-key --data-file=/path/to/private-key.pem --project=bpc-askgreg-nonprod

# Webhook secret
echo -n "your-webhook-secret" | gcloud secrets create github-webhook-secret --data-file=- --project=bpc-askgreg-nonprod

# Update secrets
gcloud secrets versions add github-app-private-key --data-file=/path/to/new-key.pem --project=bpc-askgreg-nonprod
```

## Emergency Procedures

### Stop webhook service immediately

```bash
# Stop accepting traffic
gcloud run services update code-review-webhook --no-traffic --region=europe-west1 --project=bpc-askgreg-nonprod

# Resume traffic
gcloud run services update code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod
```

### Emergency rollback

```bash
# Webhook service
gcloud run services update-traffic code-review-webhook --to-revisions=PREVIOUS_REVISION=100 --region=europe-west1 --project=bpc-askgreg-nonprod

# Agent Engine
git revert HEAD
git push origin main  # Auto-deploys
```

## Useful Links

- [Full Deployment Guide](WEBHOOK_DEPLOYMENT.md)
- [GitHub App Plan](GITHUB_APP_PLAN.md)
- [Cloud Run Console](https://console.cloud.google.com/run?project=bpc-askgreg-nonprod)
- [Agent Engine Console](https://console.cloud.google.com/vertex-ai/agents/locations/europe-west1/agent-engines/3659508948773371904?project=bpc-askgreg-nonprod)
- [Cloud Logs](https://console.cloud.google.com/logs/query?project=bpc-askgreg-nonprod)

## Makefile Commands Reference

```bash
# Agent Engine
make deploy              # Deploy agent to Vertex AI
make test               # Run unit + integration tests
make test-deploy        # Pre-deployment validation

# Webhook Service
make deploy-webhook     # Deploy webhook service to Cloud Run
make test-webhook       # Run webhook tests
make run-webhook        # Run locally
make logs-webhook       # View recent logs
make tail-webhook       # Stream logs
make status-webhook     # Check deployment status

# Development
make install           # Install dependencies
make playground        # Launch local playground
make lint             # Run linters
```
