# Webhook Service Deployment Guide

This document describes the deployment flow for the GitHub App webhook service. It explains how to deploy updates, rollback changes, and manage the production service.

## Architecture Overview

The code review bot now has **two separate deployments**:

1. **Agent Engine** - The AI agent that performs code review (already deployed)
   - Location: Vertex AI Agent Engine in `europe-west1`
   - ID: `3659508948773371904`
   - Deployed via: `make deploy` (from root directory)

2. **Webhook Service** - The Flask app that receives GitHub webhooks (new)
   - Location: Cloud Run in `europe-west1`
   - Service name: `code-review-webhook`
   - Deployed via: GitHub Actions or manual commands

These are **independent services** that can be updated separately:
- Agent Engine changes → Deploy from root with `make deploy`
- Webhook service changes → Deploy from `webhook_service/` directory


## Deployment Strategies

### Strategy 1: Automated CI/CD (Recommended for Production)

**How it works:**
- Push to `main` branch → Automatically deploys webhook service
- Separate workflow from Agent Engine deployment
- Includes pre-deployment validation and testing

**When to use:**
- Production deployments
- Team environments
- When you want deployment history and audit trail


### Strategy 2: Manual Deployment (Recommended for Development)

**How it works:**
- Run commands from your local machine
- Useful for testing and rapid iteration
- Full control over deployment process

**When to use:**
- Local development and testing
- Hotfixes that need immediate deployment
- When you want to see deployment output directly


## Setup: One-Time Configuration

Before you can deploy, complete these one-time setup steps:

### 1. Create GitHub Actions Workflow

Create `.github/workflows/deploy-webhook.yml`:

```yaml
name: Deploy Webhook Service

on:
  push:
    branches: [ main ]
    paths:
      - 'webhook_service/**'
      - '.github/workflows/deploy-webhook.yml'

permissions:
  contents: read
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: 'projects/${{ secrets.GCP_PROJECT_NUMBER }}/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider'
          service_account: 'github-actions-deployer@${{ secrets.GCP_PROJECT_ID }}.iam.gserviceaccount.com'

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Run tests
        working-directory: webhook_service
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-mock
          pytest tests/ -v || echo "Tests not yet implemented"

      - name: Build container image
        working-directory: webhook_service
        run: |
          gcloud builds submit \
            --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/code-review-webhook \
            --project ${{ secrets.GCP_PROJECT_ID }}

      - name: Deploy to Cloud Run
        working-directory: webhook_service
        run: |
          gcloud run deploy code-review-webhook \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/code-review-webhook \
            --platform managed \
            --region ${{ secrets.GCP_REGION }} \
            --allow-unauthenticated \
            --set-env-vars GITHUB_APP_ID=${{ secrets.GITHUB_APP_ID }},GCP_PROJECT_ID=${{ secrets.GCP_PROJECT_ID }},GCP_REGION=${{ secrets.GCP_REGION }},AGENT_ENGINE_ID=3659508948773371904 \
            --memory 1Gi \
            --cpu 1 \
            --timeout 300 \
            --max-instances 10 \
            --project ${{ secrets.GCP_PROJECT_ID }}

      - name: Get service URL
        run: |
          SERVICE_URL=$(gcloud run services describe code-review-webhook \
            --region ${{ secrets.GCP_REGION }} \
            --project ${{ secrets.GCP_PROJECT_ID }} \
            --format 'value(status.url)')
          echo "🚀 Webhook service deployed to: $SERVICE_URL"
          echo "📝 Update GitHub App webhook URL to: $SERVICE_URL/webhook"
```

### 2. Add GitHub Secret for App ID

The webhook service needs the GitHub App ID as an environment variable:

```bash
# Add GITHUB_APP_ID secret to your repository
gh secret set GITHUB_APP_ID -b"YOUR_GITHUB_APP_ID" -R andrewHoban/code-review
```

### 3. Add Makefile Targets

Add these targets to the root `Makefile` for convenience:

```makefile
# ==============================================================================
# Webhook Service Deployment
# ==============================================================================

# Deploy webhook service manually
deploy-webhook:
	@echo "🚀 Deploying webhook service to Cloud Run..."
	@cd webhook_service && \
	gcloud builds submit --tag gcr.io/bpc-askgreg-nonprod/code-review-webhook --project=bpc-askgreg-nonprod && \
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

# Test webhook service locally
test-webhook:
	@echo "🧪 Running webhook service tests..."
	@cd webhook_service && pip install -r requirements.txt && pip install pytest pytest-mock && pytest tests/ -v

# Run webhook service locally for development
run-webhook:
	@echo "🔧 Starting webhook service locally..."
	@cd webhook_service && \
	export GITHUB_APP_ID=${GITHUB_APP_ID} && \
	export GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET} && \
	export GCP_PROJECT_ID=bpc-askgreg-nonprod && \
	export GCP_REGION=europe-west1 && \
	python app.py
```


## Daily Workflow: How to Deploy Changes

### Scenario 1: Update Webhook Service Code

You made changes to the webhook service (e.g., fixed a bug, added a feature).

**Option A: Automated (Push to main)**

```bash
# From repository root
cd webhook_service

# Make your changes
vim app.py

# Commit and push
git add .
git commit -m "fix: improve webhook error handling"
git push origin main

# GitHub Actions automatically deploys
# Watch deployment: gh run watch
```

**Option B: Manual (Deploy directly)**

```bash
# Set environment variable
export GITHUB_APP_ID="your-app-id"

# From repository root
make deploy-webhook

# Or directly from webhook_service/
cd webhook_service
gcloud builds submit --tag gcr.io/bpc-askgreg-nonprod/code-review-webhook --project=bpc-askgreg-nonprod
gcloud run deploy code-review-webhook \
  --image gcr.io/bpc-askgreg-nonprod/code-review-webhook \
  --region europe-west1 \
  --project=bpc-askgreg-nonprod
```

### Scenario 2: Update Agent Engine (Review Logic)

You made changes to the agent code (e.g., improved prompts, added new analysis).

```bash
# From repository root
vim app/agents/python_review_pipeline.py

# Test locally first
make test

# Deploy agent engine (NOT webhook service)
make deploy

# Webhook service continues running unchanged
# It will automatically use the updated agent
```

### Scenario 3: Update Both Services

You changed both the agent logic and webhook handling.

```bash
# Deploy agent engine first
make test
make deploy

# Then deploy webhook service
export GITHUB_APP_ID="your-app-id"
make deploy-webhook

# Or push to main and let CI/CD handle both
git push origin main
```


## Deployment Commands Reference

### Check Current Deployment Status

```bash
# Check webhook service status
gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format="table(metadata.name, status.url, status.conditions[0].status)"

# Check agent engine status
gcloud ai reasoning-engines describe 3659508948773371904 \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod
```

### View Recent Deployments

```bash
# Webhook service revisions
gcloud run revisions list \
  --service=code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod

# GitHub Actions deployments
gh run list --workflow=deploy-webhook.yml
```

### View Logs

```bash
# Real-time webhook service logs
gcloud run services logs tail code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod

# Recent logs (last 50 entries)
gcloud run services logs read code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --limit=50

# Filter for errors only
gcloud run services logs read code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --log-filter='severity>=ERROR'
```

### Update Environment Variables

```bash
# Update webhook service environment variables without redeploying code
gcloud run services update code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --set-env-vars NEW_VAR=value,ANOTHER_VAR=value
```

### Update Secrets

```bash
# Update GitHub App private key
gcloud secrets versions add github-app-private-key \
  --data-file=/path/to/new-private-key.pem \
  --project=bpc-askgreg-nonprod

# Update webhook secret
echo -n "new-webhook-secret" | gcloud secrets versions add github-webhook-secret \
  --data-file=- \
  --project=bpc-askgreg-nonprod

# Restart service to pick up new secrets
gcloud run services update code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod
```


## Rollback Procedures

### Rollback Webhook Service

If a deployment causes issues, rollback to a previous revision:

```bash
# List recent revisions
gcloud run revisions list \
  --service=code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod

# Note the revision name (e.g., code-review-webhook-00005)

# Rollback to specific revision
gcloud run services update-traffic code-review-webhook \
  --to-revisions=code-review-webhook-00005=100 \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod

# Verify rollback
gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(status.traffic[0].revisionName)'
```

### Rollback Agent Engine

Agent Engine doesn't support automatic rollback. You must redeploy the previous version:

```bash
# Option 1: Revert git commits
git revert HEAD
git push origin main
# Let CI/CD redeploy

# Option 2: Check out previous commit and deploy manually
git checkout <previous-commit-hash>
make deploy
git checkout main
```

### Emergency Shutdown

If the webhook service is causing problems and you need to stop it immediately:

```bash
# Stop accepting traffic (service stays running but returns 503)
gcloud run services update code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --no-traffic

# Or delete the service entirely (can redeploy later)
gcloud run services delete code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod
```


## Testing Deployments

### Local Testing Before Deployment

```bash
# Test webhook service locally
cd webhook_service

# Set environment variables
export GITHUB_APP_ID="your-app-id"
export GITHUB_WEBHOOK_SECRET="your-webhook-secret"
export GCP_PROJECT_ID="bpc-askgreg-nonprod"

# Run locally
python app.py

# In another terminal, use ngrok
ngrok http 8080

# Update GitHub App webhook URL to ngrok URL
# Test with a real PR
```

### Staging Environment (Optional)

For safer deployments, create a staging environment:

```bash
# Deploy to staging service
gcloud run deploy code-review-webhook-staging \
  --image gcr.io/bpc-askgreg-nonprod/code-review-webhook \
  --region europe-west1 \
  --project=bpc-askgreg-nonprod \
  --set-env-vars GITHUB_APP_ID=${GITHUB_APP_ID},GCP_PROJECT_ID=bpc-askgreg-nonprod,GCP_REGION=europe-west1,AGENT_ENGINE_ID=3659508948773371904

# Create a separate GitHub App for staging
# Point it to the staging service URL
# Test with staging app

# Once validated, deploy to production
make deploy-webhook
```


## Monitoring and Alerts

### Check Service Health

```bash
# Health check endpoint
curl https://code-review-webhook-abc123-ew.a.run.app/health

# Expected response: {"status": "healthy"}
```

### Monitor Metrics

```bash
# Open Cloud Run metrics dashboard
gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(status.url)' | \
  xargs -I {} echo "Metrics: https://console.cloud.google.com/run/detail/europe-west1/code-review-webhook/metrics?project=bpc-askgreg-nonprod"
```

### Set Up Alerts (Optional)

Create alerts for critical issues:

```bash
# Example: Alert on error rate > 10%
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Webhook Service Error Rate" \
  --condition-display-name="Error rate > 10%" \
  --condition-threshold-value=0.1 \
  --condition-threshold-duration=300s \
  --project=bpc-askgreg-nonprod
```


## Troubleshooting Common Issues

### Issue: Deployment Fails with "Permission Denied"

**Solution:** Ensure service account has required roles:

```bash
# Check service account
gcloud iam service-accounts list --project=bpc-askgreg-nonprod

# Grant required roles
gcloud projects add-iam-policy-binding bpc-askgreg-nonprod \
  --member="serviceAccount:github-actions-deployer@bpc-askgreg-nonprod.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding bpc-askgreg-nonprod \
  --member="serviceAccount:github-actions-deployer@bpc-askgreg-nonprod.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
```

### Issue: Webhook Service Can't Access Agent Engine

**Solution:** Grant Cloud Run service account access:

```bash
# Get Cloud Run service account
SA=$(gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(spec.template.spec.serviceAccountName)')

# Grant Agent Engine access
gcloud projects add-iam-policy-binding bpc-askgreg-nonprod \
  --member="serviceAccount:${SA}" \
  --role="roles/aiplatform.user"
```

### Issue: Secrets Not Found

**Solution:** Verify secrets exist and are accessible:

```bash
# List secrets
gcloud secrets list --project=bpc-askgreg-nonprod

# Check secret access
gcloud secrets get-iam-policy github-app-private-key --project=bpc-askgreg-nonprod

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding github-app-private-key \
  --member="serviceAccount:${SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project=bpc-askgreg-nonprod
```

### Issue: GitHub App Not Receiving Webhooks

**Solution:** Check webhook configuration:

```bash
# Verify service URL
gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(status.url)'

# Check recent deliveries in GitHub App settings
# Go to: GitHub App → Advanced → Recent Deliveries
# Look for failed deliveries and response codes
```


## Cost Management

### Estimate Costs

Typical monthly costs for webhook service:

- **Cloud Run**: ~$5-20/month (depends on traffic)
  - First 2 million requests free
  - $0.40 per million requests after
  - $0.00002400 per vCPU-second
  - $0.00000250 per GiB-second

- **Cloud Build**: ~$0-5/month
  - First 120 build-minutes/day free

- **Container Registry**: ~$1-5/month
  - Storage costs for container images

- **Secret Manager**: ~$0.06/month
  - $0.06 per secret version accessed 10,000+ times

**Total: ~$6-30/month** depending on usage

### Reduce Costs

```bash
# Reduce min instances (increases cold start time)
gcloud run services update code-review-webhook \
  --min-instances=0 \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod

# Reduce memory (if service doesn't need 1Gi)
gcloud run services update code-review-webhook \
  --memory=512Mi \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod

# Set budget alerts
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="Code Review Bot Budget" \
  --budget-amount=50USD
```


## Best Practices

### 1. Always Test Locally First

```bash
# Run tests
cd webhook_service
pytest tests/ -v

# Test with ngrok before deploying
python app.py
# (in another terminal) ngrok http 8080
```

### 2. Use Gradual Rollouts

```bash
# Deploy new revision with 10% traffic
gcloud run services update code-review-webhook \
  --image gcr.io/bpc-askgreg-nonprod/code-review-webhook:new \
  --region europe-west1 \
  --project=bpc-askgreg-nonprod \
  --no-traffic  # Don't send traffic yet

# Gradually increase traffic
gcloud run services update-traffic code-review-webhook \
  --to-revisions=code-review-webhook-00010=10 \
  --to-revisions=code-review-webhook-00009=90 \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod
```

### 3. Tag Container Images

```bash
# Build with version tag
gcloud builds submit \
  --tag gcr.io/bpc-askgreg-nonprod/code-review-webhook:v1.2.3 \
  --project=bpc-askgreg-nonprod

# Deploy specific version
gcloud run deploy code-review-webhook \
  --image gcr.io/bpc-askgreg-nonprod/code-review-webhook:v1.2.3 \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod
```

### 4. Keep Deployment History

Track deployments in git tags:

```bash
# Tag release
git tag -a webhook-v1.2.3 -m "Deploy webhook service v1.2.3"
git push origin webhook-v1.2.3

# View deployment history
git tag -l "webhook-*"
```


## Quick Reference

```bash
# Deploy webhook service
make deploy-webhook

# Deploy agent engine
make deploy

# View webhook logs
gcloud run services logs tail code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod

# Rollback webhook
gcloud run services update-traffic code-review-webhook --to-revisions=REVISION=100 --region=europe-west1 --project=bpc-askgreg-nonprod

# Health check
curl $(gcloud run services describe code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod --format='value(status.url)')/health

# View all deployments
gh run list --workflow=deploy-webhook.yml
```
