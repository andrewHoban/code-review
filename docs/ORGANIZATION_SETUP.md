# Organization Setup Guide

**Status:** ✅ Already configured in `bpc-askgreg-nonprod` project.

This document is for reference or if setting up the code review system in a new GCP project.

## Overview

This guide covers the one-time setup required at the organization/project level to enable AI code reviews via GitHub Actions. Once set up, individual teams can adopt the workflow in minutes.

## Prerequisites

- GCP project with billing enabled
- Admin access to the GCP project
- Admin access to GitHub organization (for organization secrets)
- Agent Engine deployed (see main README)

## Setup Steps

### 1. Deploy Agent Engine

The Agent Engine must be deployed first. See the main project documentation for deployment instructions.

**Current deployment:**
- Project: `bpc-askgreg-nonprod`
- Region: `europe-west1`
- Agent Engine ID: `3659508948773371904`

### 2. Set Up Workload Identity Federation

This allows GitHub Actions to authenticate to GCP without storing service account keys.

#### 2.1 Create Workload Identity Pool

```bash
gcloud iam workload-identity-pools create github-actions-pool \
  --project=bpc-askgreg-nonprod \
  --location=global \
  --display-name="GitHub Actions Pool"
```

#### 2.2 Create Workload Identity Provider

```bash
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project=bpc-askgreg-nonprod \
  --location=global \
  --workload-identity-pool=github-actions-pool \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository_owner=='YOUR_ORG_NAME'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

Replace `YOUR_ORG_NAME` with your GitHub organization name.

#### 2.3 Create Service Account

```bash
gcloud iam service-accounts create github-actions-deployer \
  --project=bpc-askgreg-nonprod \
  --display-name="GitHub Actions Deployer"
```

#### 2.4 Grant Permissions

```bash
# Allow GitHub Actions to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding \
  github-actions-deployer@bpc-askgreg-nonprod.iam.gserviceaccount.com \
  --project=bpc-askgreg-nonprod \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository_owner/YOUR_ORG_NAME"

# Grant Agent Engine access
gcloud projects add-iam-policy-binding bpc-askgreg-nonprod \
  --member="serviceAccount:github-actions-deployer@bpc-askgreg-nonprod.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

Replace:
- `PROJECT_NUMBER` with your numeric project number
- `YOUR_ORG_NAME` with your GitHub organization name

### 3. Set Up Organization Secrets (Optional but Recommended)

Setting up organization-level secrets means teams don't need to configure secrets in each repository.

#### 3.1 In GitHub

1. Go to your GitHub organization
2. Settings → Secrets and variables → Actions
3. Click "New organization secret"
4. Add: `GCP_PROJECT_NUMBER` = your numeric project number (e.g., `442593217095`)

#### 3.2 Grant Access to Repositories

When creating the secret, you can:
- Make it available to all repositories
- Or select specific repositories

### 4. Verify Setup

Test the setup by:

1. Creating a test repository
2. Adding the workflow file (see [Team Adoption Guide](./TEAM_ADOPTION_GUIDE.md))
3. Opening a test PR
4. Checking that the workflow runs successfully

## Current Configuration

**Project:** `bpc-askgreg-nonprod`
- Project Number: `442593217095`
- Region: `europe-west1`
- Workload Identity Pool: `github-actions-pool`
- Provider: `github-provider`
- Service Account: `github-actions-deployer@bpc-askgreg-nonprod.iam.gserviceaccount.com`
- Agent Engine ID: `3659508948773371904`

## Granting Access to New Repositories

### Option 1: Organization Secrets (Recommended)

If using organization secrets:
1. Go to organization Settings → Secrets
2. Edit the `GCP_PROJECT_NUMBER` secret
3. Add the new repository to the access list

### Option 2: Repository Secrets

Each team can add the secret to their repository:
1. Repository Settings → Secrets → Actions
2. Add `GCP_PROJECT_NUMBER` secret

## Troubleshooting

### "Permission denied" errors

- Verify the service account has `roles/aiplatform.user`
- Check workload identity pool configuration
- Verify repository is in the allowed list

### "Workload identity pool not found"

- Ensure the pool and provider are created in the correct project
- Check the project number in the workflow matches the actual project

### "Service account not found"

- Verify the service account exists
- Check the service account email matches the workflow configuration

## Security Considerations

- **Least Privilege:** Service account only has `aiplatform.user` role
- **Repository Scoping:** Workload identity can be restricted to specific repositories
- **Organization Secrets:** Centralized secret management
- **No Long-Lived Keys:** Uses short-lived tokens via workload identity

## Maintenance

### Adding New Repositories

1. Add repository to organization secret access list (if using org secrets)
2. Or have team add repository secret
3. Team copies workflow file to their repo
4. Done!

### Updating Agent Engine

If the Agent Engine ID changes:
1. Update the default in `STARTER-pr-review.yml`
2. Notify teams using custom configurations
3. Update this documentation

## Support

For setup issues:
- Check GCP IAM logs
- Review GitHub Actions workflow logs
- Contact platform/infrastructure team
