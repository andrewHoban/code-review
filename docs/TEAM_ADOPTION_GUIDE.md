# AI Code Review - Team Adoption Guide

Get AI-powered code reviews in your repository in under 5 minutes!

## What You Get

- **Automatic code reviews** on every pull request
- **AI-powered suggestions** for improvements, bugs, and best practices
- **No manual setup** - just copy a workflow file
- **Free** - runs on GitHub Actions (included in your plan)

## Prerequisites

Before you start, make sure you have:

- ✅ Write access to your repository (to add workflow files)
- ✅ GitHub Actions enabled for your repository
- ✅ Access to repository secrets (or ask your repo admin)
- ✅ `GCP_PROJECT_NUMBER` secret (ask your platform/infrastructure team)

## Quick Start (5 Minutes)

### Step 1: Copy the Workflow File

1. Copy the file `.github/workflows/STARTER-pr-review.yml` from this repository
2. Paste it into your repository at: `.github/workflows/pr-review.yml`
3. Commit and push the file

**Or use the GitHub UI:**
1. Go to your repository on GitHub
2. Click "Add file" → "Create new file"
3. Name it: `.github/workflows/pr-review.yml`
4. Copy the contents from `STARTER-pr-review.yml` in this repo
5. Commit the file

### Step 2: Add Required Secret

1. Go to your repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `GCP_PROJECT_NUMBER`
4. Value: Ask your platform/infrastructure team for this (it's a numeric value like `442593217095`)
5. Click "Add secret"

**Note:** If your organization uses organization-level secrets, you may not need to add this manually.

### Step 3: Test It!

1. Open or update a pull request in your repository
2. The workflow will run automatically
3. Check the "Actions" tab to see the workflow running
4. Once complete, review comments will appear on your PR

## Configuration Options

The workflow uses these default values (you can change them in the workflow file):

- **Project ID:** `bpc-askgreg-nonprod`
- **Location:** `europe-west1`
- **Agent Engine ID:** `3659508948773371904`

If you're using a different GCP project, update these values in the workflow file.

## How It Works

1. **Trigger:** Runs automatically when a PR is opened, updated, or reopened
2. **Extraction:** Analyzes the PR changes (Python and TypeScript files)
3. **Review:** Sends changes to the AI Agent Engine for analysis
4. **Comments:** Posts review comments directly on your PR

## Supported Languages

Currently supports:
- ✅ Python
- ✅ TypeScript/JavaScript

More languages coming soon!

## Troubleshooting

### Workflow doesn't run

- Check that GitHub Actions is enabled for your repository
- Verify the workflow file is in `.github/workflows/` directory
- Check the file has `.yml` or `.yaml` extension

### "GCP_PROJECT_NUMBER secret not found"

- Add the `GCP_PROJECT_NUMBER` secret to your repository
- Contact your platform/infrastructure team to get the value
- Check if your organization uses organization-level secrets

### "Authentication failed"

- Verify the `GCP_PROJECT_NUMBER` secret is correct
- Check that your repository has access to the GCP project
- Contact your platform team if issues persist

### No review comments appear

- Check the workflow logs in the "Actions" tab
- Common reasons:
  - No supported files in the PR (only Python/TypeScript are reviewed)
  - PR is a draft (draft PRs are skipped)
  - Agent timeout (very large PRs may timeout)

### Workflow fails with "permission denied"

- Ensure the workflow has the required permissions:
  - `contents: read`
  - `pull-requests: write`
  - `id-token: write`
- These are set in the workflow file automatically

## Customization

### Skip certain files or paths

Edit the workflow to add file filters (coming soon).

### Change review behavior

The workflow uses the reusable workflow from `andrewHoban/code-review`. To customize:
1. Fork the code-review repository
2. Modify the reusable workflow
3. Update your workflow to point to your fork

## Support

- **Documentation:** See [Integration Guide](./integration_guide.md)
- **Issues:** Open an issue in the `code-review` repository
- **Questions:** Contact your platform/infrastructure team

## Example

Here's what a review looks like:

```python
# Before (reviewed code)
def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total

# AI Review Comment:
# Consider using sum() for better readability:
# return sum(item.price for item in items)
```

## Next Steps

Once you've set up the workflow:
1. ✅ Test it on a PR
2. ✅ Review the AI suggestions
3. ✅ Share with your team
4. ✅ Customize if needed

Happy coding! 🚀
