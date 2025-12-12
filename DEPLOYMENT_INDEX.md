# Deployment Documentation Index

Complete guide to deploying and managing your code review bot.

## 🎯 Where Should I Start?

### New to the deployment process?
**→ Start with [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)**
- Quick overview of the two-service architecture
- Simple deployment workflows
- Common commands you'll use daily

### Need quick commands?
**→ Use [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md)**
- Command reference table
- Common scenarios and solutions
- Troubleshooting quick fixes

### Want detailed instructions?
**→ Read [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md)**
- Complete setup instructions
- Daily workflows and best practices
- Comprehensive troubleshooting guide
- Cost management and monitoring

### Want to understand the architecture?
**→ See [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)**
- Visual ASCII diagrams
- Data flow explanations
- Security architecture
- Scaling characteristics

### Building the GitHub App?
**→ Follow [GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md)**
- Step-by-step implementation plan
- 6 milestones from start to finish
- Code examples and validation steps

### Need a printable cheatsheet?
**→ Print [.github/DEPLOYMENT_CHEATSHEET.md](.github/DEPLOYMENT_CHEATSHEET.md)**
- One-page quick reference
- Most common commands
- Emergency procedures

## 📚 Full Documentation List

### Primary Deployment Guides
| Document | Size | Purpose | When to Use |
|----------|------|---------|-------------|
| **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** | ~400 lines | Overview & getting started | First time setup |
| **[DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md)** | ~350 lines | Command reference | Daily development |
| **[WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md)** | ~4,500 lines | Complete guide | Detailed reference |

### Architecture & Planning
| Document | Size | Purpose | When to Use |
|----------|------|---------|-------------|
| **[ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)** | ~500 lines | System architecture | Understanding design |
| **[GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md)** | ~1,400 lines | Implementation plan | Building the app |
| **[DEPLOYMENT_INFO.md](DEPLOYMENT_INFO.md)** | ~150 lines | Agent Engine details | Agent Engine reference |

### Quick References
| Document | Size | Purpose | When to Use |
|----------|------|---------|-------------|
| **[.github/DEPLOYMENT_CHEATSHEET.md](.github/DEPLOYMENT_CHEATSHEET.md)** | ~100 lines | Ultra-quick reference | Quick lookup |
| **[DEPLOYMENT_IMPLEMENTATION_SUMMARY.md](DEPLOYMENT_IMPLEMENTATION_SUMMARY.md)** | ~600 lines | What was built | Understanding changes |

### Integration & Setup
| Document | Size | Purpose | When to Use |
|----------|------|---------|-------------|
| **[docs/integration_guide.md](docs/integration_guide.md)** | ~300 lines | GitHub Actions integration | Setting up workflows |
| **[README.md](README.md)** | ~460 lines | Project overview | Getting started |

## 🎬 Common Scenarios

### "I want to deploy my changes"
1. Make changes to code
2. Run `git push origin main`
3. ✅ Done! Auto-deploys

→ See [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#daily-workflow-how-to-deploy-changes)

### "I need to deploy a hotfix immediately"
1. Run `make test`
2. Run `make deploy` (for agent) or `make deploy-webhook` (for webhook)
3. Monitor with `make logs-webhook`

→ See [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md#scenario-1-update-review-logic)

### "Something broke, I need to rollback"
1. List revisions: `gcloud run revisions list --service=code-review-webhook --region=europe-west1 --project=bpc-askgreg-nonprod`
2. Rollback: `gcloud run services update-traffic code-review-webhook --to-revisions=REVISION=100 --region=europe-west1 --project=bpc-askgreg-nonprod`

→ See [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md#rollback-procedures)

### "I want to test locally before deploying"
1. Set env vars: `export GITHUB_APP_ID="..." GITHUB_WEBHOOK_SECRET="..."`
2. Run `make run-webhook`
3. In another terminal: `ngrok http 8080`

→ See [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#local-development-workflow)

### "How much will this cost?"
- ~$0.01-0.05 per PR reviewed
- ~$10-60/month for typical usage

→ See [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md#cost-structure)

### "How do I monitor the service?"
```bash
make status-webhook    # Check status
make logs-webhook      # Recent logs
make tail-webhook      # Live logs
```

→ See [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md#monitor)

### "I'm getting permission errors"
Check authentication and IAM roles

→ See [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md#troubleshooting-common-issues)

## 📖 Learning Path

### Level 1: Getting Started (30 minutes)
1. Read [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)
2. Skim [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md)
3. Try: `make deploy` or `make deploy-webhook`

**Goal**: Understand the two-service architecture and basic deployment

### Level 2: Daily Development (1 hour)
1. Read [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md) in detail
2. Practice: Make a change and deploy it
3. Learn: `make logs-webhook` and `make status-webhook`

**Goal**: Become comfortable with daily deployment workflow

### Level 3: Deep Understanding (3 hours)
1. Read [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md)
2. Study [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)
3. Practice: Test locally with ngrok, deploy, rollback

**Goal**: Understand full deployment lifecycle and troubleshooting

### Level 4: Expert (Ongoing)
1. Review [GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md) for implementation details
2. Experiment with monitoring, alerts, and optimization
3. Contribute improvements to deployment process

**Goal**: Master the deployment system and optimize it

## 🔍 Find Information By Topic

### Deployment
- **Automated deployment**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#simple-flow-recommended)
- **Manual deployment**: [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md#deploy)
- **Pre-deployment validation**: [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md#testing-deployments)
- **Deployment strategies**: [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md#deployment-strategies)

### Monitoring
- **View logs**: [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md#monitor)
- **Check status**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#key-commands-youll-use-daily)
- **Set up alerts**: [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md#monitoring-and-alerts)
- **Cloud Console links**: [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md#useful-links)

### Troubleshooting
- **Quick fixes**: [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md#troubleshooting)
- **Common issues**: [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md#troubleshooting-common-issues)
- **Permission errors**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#quick-troubleshooting)
- **Emergency procedures**: [DEPLOYMENT_CHEATSHEET.md](.github/DEPLOYMENT_CHEATSHEET.md#-troubleshooting)

### Architecture
- **System overview**: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md#system-architecture)
- **Data flow**: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md#data-flow)
- **Security**: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md#security-architecture)
- **Scaling**: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md#scaling-characteristics)

### Costs
- **Cost breakdown**: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md#cost-structure)
- **Cost optimization**: [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md#cost-management)
- **Usage estimates**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#cost-expectations)

### Development
- **Local testing**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md#setup-one-time-only)
- **Running locally**: [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md#test-locally)
- **Testing strategies**: [docs/testing-guidelines.md](docs/testing-guidelines.md)
- **Integration guide**: [docs/integration_guide.md](docs/integration_guide.md)

### GitHub App
- **Implementation plan**: [GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md)
- **Setup instructions**: [GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md#concrete-steps)
- **Testing**: [GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md#validation-and-acceptance)
- **Deployment strategy**: [GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md#deployment-strategy)

## 🛠️ Key Commands Quick Reference

```bash
# Deployment
make deploy              # Deploy Agent Engine
make deploy-webhook      # Deploy Webhook Service

# Testing
make test               # Run all tests
make test-webhook       # Test webhook service
make run-webhook        # Run locally

# Monitoring
make status-webhook     # Check status
make logs-webhook       # Recent logs
make tail-webhook       # Live logs

# Development
make playground         # Test agent locally
make install           # Install dependencies
make lint              # Run linters
```

## 📞 Getting Help

### Where to look for answers:

1. **Quick answer needed?**
   → [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md)

2. **How do I...?**
   → [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)

3. **Something's broken**
   → [WEBHOOK_DEPLOYMENT.md - Troubleshooting](WEBHOOK_DEPLOYMENT.md#troubleshooting-common-issues)

4. **I want to understand why**
   → [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)

5. **I need to build it from scratch**
   → [GITHUB_APP_PLAN.md](GITHUB_APP_PLAN.md)

### Still stuck?

Check these resources:
- Cloud Run logs: `make logs-webhook`
- GitHub Actions logs: `gh run list`
- Cloud Console: [Links in Quick Reference](DEPLOYMENT_QUICK_REFERENCE.md#useful-links)

## 🎯 Success Checklist

After reading the deployment docs, you should be able to:

- [ ] Deploy the agent engine with `make deploy`
- [ ] Deploy the webhook service with `make deploy-webhook`
- [ ] Understand when to use automated vs manual deployment
- [ ] Check deployment status with `make status-webhook`
- [ ] View logs with `make logs-webhook`
- [ ] Rollback if needed
- [ ] Test locally before deploying
- [ ] Estimate monthly costs
- [ ] Troubleshoot common issues
- [ ] Find answers in the documentation

## 📝 Document Change Log

### 2025-12-12
- Created comprehensive deployment documentation
- Added GitHub Actions workflow for webhook service
- Updated Makefile with webhook deployment targets
- Created quick reference guides and cheatsheets
- Added architecture diagrams and cost breakdowns

---

**Quick Links:**
- [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md) - Start here
- [DEPLOYMENT_QUICK_REFERENCE.md](DEPLOYMENT_QUICK_REFERENCE.md) - Command reference
- [WEBHOOK_DEPLOYMENT.md](WEBHOOK_DEPLOYMENT.md) - Complete guide
- [README.md](README.md) - Project overview
