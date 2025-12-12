# 🚀 Deployment Cheatsheet

Quick reference for deploying the code review bot. Keep this handy!

## 📦 Two Services, Two Deploy Commands

| Service | Command | When? |
|---------|---------|-------|
| 🤖 **Agent Engine** | `make deploy` | Changed `app/` |
| 🪝 **Webhook Service** | `make deploy-webhook` | Changed `webhook_service/` |

## ⚡ Quick Deploy

### Automated (Easiest)
```bash
git add .
git commit -m "your changes"
git push origin main
# ✨ Auto-deploys based on what changed!
```

### Manual (For hotfixes)
```bash
# Agent Engine
make deploy

# Webhook Service
export GITHUB_APP_ID="123456"
make deploy-webhook
```

## 📊 Monitor

```bash
make status-webhook    # Is it running?
make logs-webhook      # Recent logs
make tail-webhook      # Live logs
```

## 🔄 Rollback

```bash
# Webhook Service
gcloud run revisions list --service=code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod
gcloud run services update-traffic code-review-webhook --to-revisions=REVISION=100 --region=europe-west1 --project=bpc-askgreg-nonprod

# Agent Engine
git checkout PREVIOUS_COMMIT
make deploy
git checkout main
```

## 🧪 Test Before Deploy

```bash
make test              # All tests
make test-webhook      # Webhook tests only
make run-webhook       # Run locally
```

## 🆘 Troubleshooting

### "Webhook not receiving events"
```bash
make logs-webhook
# Check GitHub App webhook URL matches service URL + /webhook
```

### "Permission denied"
```bash
gcloud auth login
gcloud config set project bpc-askgreg-nonprod
```

### "Agent timeout"
```bash
# Increase timeout
gcloud run services update code-review-webhook --timeout=600 --region=europe-west1 --project=bpc-askgreg-nonprod
```

## 📚 Full Docs

- [DEPLOYMENT_SUMMARY.md](../DEPLOYMENT_SUMMARY.md) - Overview
- [DEPLOYMENT_QUICK_REFERENCE.md](../DEPLOYMENT_QUICK_REFERENCE.md) - Commands
- [WEBHOOK_DEPLOYMENT.md](../WEBHOOK_DEPLOYMENT.md) - Complete guide

## 💰 Cost

~$0.01-0.05 per PR reviewed
~$10-60/month for typical usage

## 🔗 Console Links

- [Cloud Run](https://console.cloud.google.com/run?project=bpc-askgreg-nonprod)
- [Agent Engine](https://console.cloud.google.com/vertex-ai/agents/locations/europe-west1/agent-engines/3659508948773371904?project=bpc-askgreg-nonprod)
- [Logs](https://console.cloud.google.com/logs/query?project=bpc-askgreg-nonprod)
