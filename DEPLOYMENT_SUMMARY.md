# Deployment Summary - Code Review Bot

## What You Have Now

Your code review bot consists of **two independent services**:

### 1. Agent Engine (Already Deployed ✅)
- **Purpose**: Performs AI-powered code review
- **Location**: Vertex AI Agent Engine, `europe-west1`
- **ID**: `3659508948773371904`
- **Deploy with**: `make deploy`
- **Update when**: Changing review logic, prompts, or analysis

### 2. Webhook Service (To Be Implemented)
- **Purpose**: Receives GitHub webhooks and orchestrates reviews
- **Location**: Cloud Run, `europe-west1`
- **Deploy with**: `make deploy-webhook`
- **Update when**: Changing GitHub integration or webhook handling

## Your Deployment Flow

### Simple Flow (Recommended)
```bash
# Step 1: Make changes
vim app/agent.py                    # Change review logic
vim webhook_service/app.py          # Change webhook handling

# Step 2: Commit and push
git add .
git commit -m "feat: improve reviews"
git push origin main

# Step 3: GitHub Actions automatically deploys!
# - Agent Engine updates if app/ changed
# - Webhook Service updates if webhook_service/ changed
```

### Manual Flow (For Hotfixes)
```bash
# Deploy Agent Engine
make test
make deploy

# Deploy Webhook Service
export GITHUB_APP_ID="your-app-id"
make deploy-webhook
```

## Key Commands You'll Use Daily

### Deployment
| Command | What it does | When to use |
|---------|-------------|-------------|
| `make deploy` | Deploy Agent Engine | Changed review logic |
| `make deploy-webhook` | Deploy Webhook Service | Changed GitHub integration |
| `make test` | Run all tests | Before deploying |

### Monitoring
| Command | What it does |
|---------|-------------|
| `make status-webhook` | Check webhook service status |
| `make logs-webhook` | View recent logs |
| `make tail-webhook` | Stream logs in real-time |

### Development
| Command | What it does |
|---------|-------------|
| `make run-webhook` | Run webhook service locally |
| `make test-webhook` | Test webhook service |
| `make playground` | Launch agent playground |

## When to Deploy What?

### Changed `app/` directory? → Deploy Agent Engine
Examples:
- Modified `app/agents/python_review_pipeline.py`
- Updated `app/prompts/core_principles.py`
- Changed `app/tools/python_tools.py`

**Deploy with**: `make deploy`

### Changed `webhook_service/` directory? → Deploy Webhook Service
Examples:
- Modified `webhook_service/app.py`
- Updated `webhook_service/github_client.py`
- Changed `webhook_service/config.py`

**Deploy with**: `make deploy-webhook`

### Changed both? → Deploy both (Agent Engine first)
```bash
make deploy                 # Deploy agent first
make deploy-webhook        # Then webhook service
```

## Setup (One Time Only)

Before you can use the deployment commands, you need:

### 1. GitHub Repository Secret
```bash
gh secret set GITHUB_APP_ID -b"your-github-app-id"
```

### 2. Google Cloud Secrets
```bash
# GitHub App private key
gcloud secrets create github-app-private-key \
  --data-file=/path/to/private-key.pem \
  --project=bpc-askgreg-nonprod

# Webhook secret
echo -n "your-webhook-secret" | \
  gcloud secrets create github-webhook-secret \
  --data-file=- \
  --project=bpc-askgreg-nonprod
```

### 3. Environment Variables (for manual deployment)
```bash
export GITHUB_APP_ID="your-app-id"
export GITHUB_WEBHOOK_SECRET="your-webhook-secret"
```

## Quick Troubleshooting

### Problem: Webhook not receiving events
```bash
# Check service is running
make status-webhook

# Check logs for errors
make logs-webhook

# Verify webhook URL in GitHub App settings
gcloud run services describe code-review-webhook \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod \
  --format='value(status.url)'
```

### Problem: Permission denied during deployment
```bash
# Ensure you're authenticated
gcloud auth login
gcloud config set project bpc-askgreg-nonprod

# Check your permissions
gcloud projects get-iam-policy bpc-askgreg-nonprod \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

### Problem: Agent Engine timeout
```bash
# Check Agent Engine logs
gcloud logging read \
  "resource.type=aiplatform.googleapis.com/ReasoningEngine" \
  --project=bpc-askgreg-nonprod \
  --limit=20

# Increase webhook timeout if needed
gcloud run services update code-review-webhook \
  --timeout=600 \
  --region=europe-west1 \
  --project=bpc-askgreg-nonprod
```

### Problem: Need to rollback
```bash
# Rollback webhook service
gcloud run revisions list --service=code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod
gcloud run services update-traffic code-review-webhook --to-revisions=REVISION_NAME=100 --region=europe-west1 --project=bpc-askgreg-nonprod

# Rollback agent engine (redeploy previous commit)
git log --oneline -10  # Find previous working commit
git checkout COMMIT_HASH
make deploy
git checkout main
```

## Cost Expectations

### Per Pull Request
- Agent Engine: ~$0.01-0.05 per PR (Gemini API usage)
- Webhook Service: ~$0.0001 per PR (Cloud Run execution)
- **Total**: ~$0.01-0.05 per PR

### Monthly (Typical Usage)
- **10 PRs/day**: ~$10-20/month
- **50 PRs/day**: ~$30-60/month
- **200 PRs/day**: ~$100-200/month

Most cost is from Gemini API (Agent Engine). Cloud Run costs are minimal.

## Architecture at a Glance

```
Developer opens PR
      ↓
GitHub sends webhook
      ↓
Webhook Service (Cloud Run)
  • Validates signature
  • Extracts PR context
  • Calls Agent Engine →
      ↓
Agent Engine (Vertex AI)
  • Analyzes code
  • Checks style
  • Reviews tests
  • Synthesizes feedback
      ↓
Webhook Service
  • Posts comments to GitHub
      ↓
Review appears on PR ✨
```

## Documentation Map

| Document | Purpose | When to read |
|----------|---------|-------------|
| **DEPLOYMENT_SUMMARY.md** (this file) | Quick overview | Start here! |
| **DEPLOYMENT_QUICK_REFERENCE.md** | Common commands | Daily use |
| **WEBHOOK_DEPLOYMENT.md** | Complete deployment guide | Detailed reference |
| **GITHUB_APP_PLAN.md** | Implementation plan | Building the GitHub App |
| **ARCHITECTURE_DIAGRAM.md** | System architecture | Understanding the system |
| **DEPLOYMENT_INFO.md** | Agent Engine deployment | Agent Engine details |

## Next Steps

### If you haven't built the GitHub App yet:
1. Read `GITHUB_APP_PLAN.md`
2. Follow milestones 1-6
3. Come back here for deployment commands

### If the GitHub App is already built:
1. Set up one-time secrets (see Setup section above)
2. Deploy with `make deploy-webhook`
3. Update GitHub App webhook URL
4. Test with a PR!

### Daily development workflow:
1. Make changes to code
2. Test locally: `make run-webhook` or `make playground`
3. Commit and push to main
4. GitHub Actions deploys automatically
5. Monitor with `make logs-webhook`

## Getting Help

### View logs
```bash
make logs-webhook              # Recent webhook logs
make tail-webhook             # Stream webhook logs
gcloud logging read ...       # Agent Engine logs
```

### Check status
```bash
make status-webhook           # Webhook service status
gcloud ai reasoning-engines describe 3659508948773371904 --region=europe-west1 --project=bpc-askgreg-nonprod  # Agent Engine status
```

### Test health
```bash
# Webhook service
SERVICE_URL=$(gcloud run services describe code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod --format='value(status.url)')
curl $SERVICE_URL/health

# Should return: {"status": "healthy"}
```

### Console links
- [Cloud Run Console](https://console.cloud.google.com/run?project=bpc-askgreg-nonprod)
- [Agent Engine Console](https://console.cloud.google.com/vertex-ai/agents/locations/europe-west1/agent-engines/3659508948773371904?project=bpc-askgreg-nonprod)
- [Cloud Logs](https://console.cloud.google.com/logs/query?project=bpc-askgreg-nonprod)
- [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=bpc-askgreg-nonprod)

## Remember

✅ **Two services**: Agent Engine (review logic) + Webhook Service (GitHub integration)

✅ **Independent deployments**: Update one without affecting the other

✅ **Automated by default**: Push to main → Auto-deploys

✅ **Manual when needed**: `make deploy` or `make deploy-webhook`

✅ **Monitor easily**: `make logs-webhook` or `make tail-webhook`

✅ **Rollback available**: Previous revisions kept automatically

That's it! You now have a complete deployment strategy for your code review bot. 🚀
