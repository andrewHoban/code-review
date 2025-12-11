# Deployment Setup Summary

This document summarizes the deployment automation setup completed on 2025-12-11.

## ✅ Completed Setup

### 1. GitHub Repository
- **Repository**: `andrewHoban/code-review`
- **URL**: https://github.com/andrewHoban/code-review
- **Branch**: `main` (created from `master`)

### 2. GitHub Actions Workflows
- **CI Workflow** (`.github/workflows/ci.yml`): Runs on PRs and feature branch pushes
  - Linters (Ruff, MyPy)
  - Unit tests
  - Integration tests
  - Pre-deployment validation

- **Deploy Workflow** (`.github/workflows/deploy.yml`): Runs on pushes to `main`
  - Authenticates via Workload Identity Federation
  - Runs pre-deployment validation
  - Deploys to Agent Engine
  - Verifies deployment

### 3. Git Hooks
- **Pre-commit hooks**: Auto-format code, check YAML, run type checking
- **Pre-push hooks**: Run unit tests, integration tests, and pre-deployment validation
- **Location**: `.git/hooks/pre-commit` and `.git/hooks/pre-push`

### 4. GitHub Secrets
Configured in repository:
- `GCP_PROJECT_ID`: `bpc-askgreg-nonprod`
- `GCP_PROJECT_NUMBER`: `442593217095`
- `GCP_REGION`: `europe-west1`

### 5. GCP Resources
- **Workload Identity Pool**: `github-actions-pool` (created)
- **Service Account**: `github-actions-deployer@bpc-askgreg-nonprod.iam.gserviceaccount.com` (created)
- **IAM Permissions**:
  - `roles/aiplatform.user`
  - `roles/storage.admin`
  - `roles/iam.workloadIdentityUser` (bound to repository)

### 6. Documentation
- **Deployment Rules**: `.cursor/rules/deployment.mdc`
- **Updated README**: Added deployment section
- **Updated Agents Rules**: References deployment.mdc

## ⚠️ Pending: Workload Identity Provider

The Workload Identity Provider (`github-provider`) could not be created via CLI due to GCP API validation requirements.

**Action Required**: Create the provider manually via GCP Console:

1. Navigate to: https://console.cloud.google.com/iam-admin/workload-identity-pools
2. Select project: `bpc-askgreg-nonprod`
3. Click on pool: `github-actions-pool`
4. Click "Add Provider"
5. Select "OpenID Connect (OIDC)"
6. Configure:
   - **Name**: `github-provider`
   - **Issuer URL**: `https://token.actions.githubusercontent.com`
   - **Attribute mapping**:
     - `google.subject` = `assertion.sub`
     - `attribute.repository` = `assertion.repository`
7. Save

Alternatively, use the Terraform configuration or gcloud command with proper attribute conditions.

**Note**: The deployment workflow will fail until this provider is created. The CI workflow will work fine without it.

## Testing the Setup

### Test Pre-Push Hooks
```bash
# Make a change
echo "# test" >> app/config.py
git add app/config.py
git commit -m "test: verify hooks"
git push  # Should run tests automatically
```

### Test CI Workflow
```bash
# Create a feature branch
git checkout -b feature/test-ci
# Make changes and push
git push -u origin feature/test-ci
# Create PR
gh pr create --title "Test CI" --body "Testing CI workflow"
```

### Test Deployment
```bash
# Merge PR to main (or push directly to main)
# GitHub Actions will automatically deploy
gh run watch  # Watch the deployment
```

## Verification Commands

```bash
# Check workflows
gh workflow list --repo andrewHoban/code-review

# Check secrets
gh secret list --repo andrewHoban/code-review

# Check branch protection
gh api repos/andrewHoban/code-review/branches/main/protection

# Check GCP resources
gcloud iam workload-identity-pools describe github-actions-pool \
  --location=global --project=bpc-askgreg-nonprod

# List service accounts
gcloud iam service-accounts list --project=bpc-askgreg-nonprod | grep github-actions
```

## ✅ Required APIs Enabled

The following Google Cloud APIs have been enabled:
- **IAM Service Account Credentials API** (`iamcredentials.googleapis.com`) - Required for Workload Identity Federation
- **Cloud Resource Manager API** (`cloudresourcemanager.googleapis.com`) - Required for project resource management
- **Vertex AI API** (`aiplatform.googleapis.com`) - Required for Agent Engine deployment

## Next Steps

1. **Create Workload Identity Provider** (see above) - ✅ **COMPLETED** (if you've already done this)
2. ~~**Enable Required APIs**~~ - ✅ **COMPLETED**
3. **Test deployment workflow** by pushing to main
4. **Monitor first deployment** in GitHub Actions and GCP Console

## Troubleshooting

### Pre-push hooks not running
- Ensure hooks are executable: `chmod +x .git/hooks/pre-push`
- Reinstall pre-commit: `uv run pre-commit install`

### Deployment fails in CI
- Check GitHub Actions logs
- Verify Workload Identity Provider exists
- Verify service account has correct permissions
- Check Agent Engine logs in GCP Console

### Tests fail locally but pass in CI
- Ensure dependencies are installed: `make install`
- Check Python version matches (3.10)
- Verify environment variables are set
