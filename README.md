# Code Review Agent

A demo multi-language code review agent for GitHub PRs, built with Google's Agent Development Kit (ADK).

## Overview

This agent analyzes pull requests and provides structured feedback for Python and TypeScript code. It uses a single LLM-based agent that performs comprehensive code review using direct reasoning, applying review principles for correctness, security, performance, design quality, and test coverage.

## 🚀 Quick Start: Deployment

Your bot has **two services** that deploy independently:

| Service | Deploy Command | When to Update |
|---------|---------------|----------------|
| 🤖 **Agent Engine** (AI Logic) | `make deploy` | Changed review logic in `app/` |
| 🪝 **Webhook Service** (GitHub) | `make deploy-webhook` | Changed integration in `webhook_service/` |

**Automated deployment**: Just push to `main` and it auto-deploys! 🎉

```bash
git push origin main  # Auto-deploys based on what changed
```

**Manual deployment**: For hotfixes or testing
```bash
make deploy              # Deploy agent
make deploy-webhook      # Deploy webhook (requires GITHUB_APP_ID env var)
```

## Features

- **Multi-Language Support**: Python and TypeScript with unified review approach
- **Comprehensive Review**: Checks correctness, security, performance, design, and test quality
- **Structured Output**: Markdown format with inline comments ready for GitHub API integration
- **Efficient Architecture**: Single LLM agent with optimized prompt engineering
- **Production Ready**: Deployed to Agent Engine with observability and telemetry
- **Automated PR Reviews**: Automatically reviews PRs and posts comments via GitHub Actions

## Architecture

```
CodeReviewer Agent (gemini-2.5-pro)
  │
  └─ Single LLM Agent
      ├─ Receives: PR metadata + changed files + context
      ├─ Applies: Review principles (correctness, security, design, tests)
      └─ Returns: Structured markdown review with inline comments
```

The agent uses direct LLM reasoning to analyze code, applying comprehensive review principles for:
- **Correctness**: Logic errors, edge cases, resource leaks
- **Security**: Injection vulnerabilities, secrets, input validation
- **Performance**: Obvious bottlenecks, N+1 queries
- **Design**: SOLID, DRY, YAGNI principles
- **Test Quality**: Coverage gaps, test anti-patterns

## Quick Start

### Installation

```bash
make install
```

### Local Testing

```bash
make playground
```

### Run Tests

```bash
# Run fast tests (unit + integration, excludes E2E)
make test

# Run all tests including E2E (slow - real API calls)
make test-all
```

## Usage

### Automated PR Reviews

The agent automatically reviews pull requests when they are opened or updated. The workflow:
1. Extracts changed files and context from the PR
2. Calls the deployed agent via Agent Engine API
3. Posts review comments and summary on the PR

**Setup:**
- The workflow (`.github/workflows/pr-review.yml`) is already configured
- Requires GitHub Secrets: `GCP_PROJECT_ID`, `GCP_PROJECT_NUMBER`, `GCP_REGION`
- Uses Workload Identity Federation for GCP authentication

**Manual Usage:**

The agent accepts structured JSON input with PR metadata and review context. See [`docs/integration_guide.md`](docs/integration_guide.md) for detailed integration instructions.

### Example Input

```json
{
  "pr_metadata": {
    "pr_number": 123,
    "repository": "owner/repo",
    "title": "Fix authentication bug",
    "author": "developer",
    "base_branch": "main",
    "head_branch": "feature"
  },
  "review_context": {
    "changed_files": [
      {
        "path": "src/auth.py",
        "language": "python",
        "status": "modified",
        "full_content": "...",
        "diff": "..."
      }
    ],
    "related_files": [...],
    "test_files": [...]
  }
}
```

### Example Output

```json
{
  "summary": "## Code Review Summary\n...",
  "inline_comments": [
    {
      "path": "src/auth.py",
      "line": 42,
      "side": "RIGHT",
      "body": "⚠️ **Issue**: ...",
      "severity": "error"
    }
  ],
  "overall_status": "NEEDS_CHANGES",
  "metrics": {
    "files_reviewed": 3,
    "issues_found": 7,
    "critical_issues": 2
  }
}
```

## Project Structure

```
app/
├── models/          # Input/output schemas
├── prompts/         # Review principles and context
├── tools/           # Repository context tools (optional)
├── utils/           # Helper utilities (input prep, security)
├── app_utils/       # Deployment and telemetry utilities
├── config.py        # Configuration
├── agent.py         # Single code review agent
└── agent_engine_app.py  # Agent Engine entrypoint

tests/
├── unit/            # Unit tests
├── integration/     # Integration tests
├── e2e/             # End-to-end tests
└── fixtures/        # Test data

docs/
├── testing-guidelines.md
└── integration_guide.md

scripts/
├── extract_review_context.py  # Extract PR context
├── call_agent.py              # Call Agent Engine API
└── post_review.py             # Post review comments
```

## Testing

See [`docs/testing-guidelines.md`](docs/testing-guidelines.md) for comprehensive testing documentation.

```bash
# Run all fast tests (unit + integration, excludes E2E)
pytest -m "not e2e"

# Run only unit tests
pytest tests/unit

# Run only integration tests (fast, no API calls)
pytest tests/integration

# Run E2E tests (real API calls - slow!)
pytest -m "e2e" tests/e2e/

# Run with coverage
pytest --cov=app --cov-report=html -m "not e2e"
```

**Note:** Integration tests are fast (<1s each) and use mocked contexts. E2E tests make real API calls and are slow (20+ seconds each). Use `-m "not e2e"` to skip E2E tests in regular development.

## Deployment

The code review bot has **two independent services** that deploy separately:

### 1. Agent Engine (AI Review Logic)
Deployed to Vertex AI Agent Engine. Update when changing review logic or prompts.

```bash
# Automated: Push to main branch
git push origin main  # Auto-deploys if app/ changed

# Manual deployment
make test       # Run tests first
make deploy     # Deploy to Agent Engine
```

### 2. Webhook Service (GitHub Integration)
Deployed to Cloud Run. Update when changing GitHub integration or webhook handling.

```bash
# Automated: Push to main branch
git push origin main  # Auto-deploys if webhook_service/ changed

# Manual deployment
export GITHUB_APP_ID="your-app-id"
make deploy-webhook  # Deploy to Cloud Run
```

### Quick Commands
```bash
make deploy              # Deploy Agent Engine
make deploy-webhook      # Deploy Webhook Service
make status-webhook      # Check webhook status
make logs-webhook        # View webhook logs
make test               # Run all tests
```

### Deployment Resources

For deployment details, see the deployment workflows in `.github/workflows/` and the `Makefile` for common commands.

## Adding to Your Deployment Pipeline

This section provides step-by-step instructions for integrating the code review agent into your own repository's CI/CD pipeline.

### Prerequisites

Before adding the review bot to your pipeline, ensure you have:

1. **GCP Project Setup:**
   - A Google Cloud Platform project with billing enabled
   - Vertex AI API enabled (`aiplatform.googleapis.com`)
   - IAM Service Account Credentials API enabled (`iamcredentials.googleapis.com`)
   - Cloud Resource Manager API enabled (`cloudresourcemanager.googleapis.com`)

2. **Agent Deployment:**
   - The code review agent deployed to Agent Engine (see [Deployment](#deployment) section)
   - Your Agent Engine ID (found in `DEPLOYMENT_INFO.md` or GCP Console)

3. **GitHub Setup:**
   - GitHub repository with Actions enabled
   - Workload Identity Federation configured for GCP authentication
   - Service account with appropriate permissions

### Option 1: Using the Reusable Workflow (Recommended)

The easiest way to add code review to your repository is using the reusable workflow:

1. **Create a workflow file** in your repository at `.github/workflows/code-review.yml`:

```yaml
name: Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    uses: YOUR_ORG/code-review/.github/workflows/pr-review-reusable.yml@main
    with:
      project_id: "your-gcp-project-id"
      location: "europe-west1"  # or your deployment region
      agent_engine_id: "YOUR_AGENT_ENGINE_ID"
    secrets:
      GCP_PROJECT_NUMBER: ${{ secrets.GCP_PROJECT_NUMBER }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

2. **Set up GitHub Secrets:**
   - Go to your repository Settings → Secrets and variables → Actions
   - Add `GCP_PROJECT_NUMBER` (your GCP project number, not ID)

3. **Configure Workload Identity Federation:**
   - Follow [Google's Workload Identity Federation guide](https://cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
   - Create a workload identity pool and provider for GitHub Actions
   - Grant the service account permission to call Agent Engine API

4. **Test the integration:**
   - Create a test PR with Python or TypeScript changes
   - The workflow should automatically trigger and post review comments

### Option 2: Custom Workflow (Full Control)

If you need more control or customization, create a custom workflow:

1. **Copy the workflow file** from this repository:
   ```bash
   # Copy the workflow
   cp .github/workflows/pr-review.yml /path/to/your/repo/.github/workflows/
   ```

2. **Copy the scripts** to your repository:
   ```bash
   # Copy scripts directory
   cp -r scripts /path/to/your/repo/
   ```

3. **Update the workflow** with your specific values:
   - Replace `agent-engine-id` with your Agent Engine ID
   - Update `location` to match your deployment region
   - Adjust any paths if your repository structure differs

4. **Set up dependencies:**
   - Ensure your repository has `pyproject.toml` or `requirements.txt` with:
     - `PyGithub`
     - `GitPython`
     - `google-cloud-aiplatform`
   - Or use `uv` and copy the dependency management from this repo

5. **Configure secrets and authentication** as described in Option 1

### Option 3: Manual Integration (API Calls)

For custom CI/CD systems or non-GitHub workflows:

1. **Extract review context** using the script:
   ```bash
   python scripts/extract_review_context.py \
     --repo-path="/path/to/repo" \
     --pr-number=123 \
     --repository="owner/repo" \
     --base-sha="base_commit" \
     --head-sha="head_commit" \
     --github-token="YOUR_TOKEN" \
     --output=review_payload.json
   ```

2. **Call the agent** via Agent Engine API:
   ```bash
   python scripts/call_agent.py \
     --payload=review_payload.json \
     --output=review_response.json \
     --project-id="your-project-id" \
     --location="your-region" \
     --agent-engine-id="YOUR_ENGINE_ID"
   ```

3. **Post review comments**:
   ```bash
   python scripts/post_review.py \
     --response=review_response.json \
     --repository="owner/repo" \
     --pr-number=123 \
     --github-token="YOUR_TOKEN" \
     --create-review
   ```

### Configuration Options

#### Workflow Triggers

Customize when reviews run by modifying the `on:` section:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]  # Review on open/update
    paths:
      - '**.py'      # Only review Python files
      - '**.ts'       # Only review TypeScript files
      - '**.tsx'      # Include TSX files
```

#### Review Scope

The agent automatically:
- Reviews only Python and TypeScript files
- Skips files larger than 100KB
- Analyzes related files (imports, dependencies)
- Includes test files in analysis

#### Error Handling

The workflow includes error handling:
- Continues on errors (won't block PRs)
- Logs detailed error messages
- Handles rate limits gracefully
- Skips PRs with no supported files

### Troubleshooting

**Workflow doesn't trigger:**
- Check that Actions are enabled in repository settings
- Verify the workflow file is in `.github/workflows/`
- Ensure the PR is not a draft (workflow skips drafts)

**Authentication errors:**
- Verify Workload Identity Federation is configured
- Check service account has `aiplatform.reasoningEngines.query` permission
- Ensure `GCP_PROJECT_NUMBER` secret is set correctly

**Agent timeout:**
- Large PRs (>20 files) may timeout
- Consider splitting large PRs or increasing timeout in agent config
- Check Agent Engine logs in GCP Console

**No review comments posted:**
- Check workflow logs for errors
- Verify Agent Engine ID is correct
- Ensure PR contains Python or TypeScript files
- Check that `GITHUB_TOKEN` has write permissions

### Advanced Configuration

#### Custom Agent Engine

To use a different Agent Engine instance:

1. Deploy your own agent (see [Deployment](#deployment))
2. Update the `agent-engine-id` in your workflow
3. Ensure the agent uses the same input/output schema

#### Custom Review Criteria

Modify the agent code to:
- Add custom review rules
- Support additional languages
- Change severity thresholds
- Customize output format

See the [Integration Guide](docs/integration_guide.md) for detailed API documentation.

### Cost Considerations

- **Agent Engine:** Pay per query (see [Vertex AI pricing](https://cloud.google.com/vertex-ai/pricing))
- **GitHub Actions:** Free for public repos, usage-based for private
- **API Calls:** Minimal cost for typical PR reviews

**Optimization tips:**
- Only review on PR open/update (not on every commit)
- Skip draft PRs (already configured)
- Limit file count per review
- Cache results for unchanged files

## Documentation

### User Documentation
- [Testing Guidelines](docs/testing-guidelines.md) - Comprehensive testing strategy
- [Integration Guide](docs/integration_guide.md) - GitHub Actions integration

### Deployment Documentation

See the deployment workflows in `.github/workflows/` for automated deployment configuration.

## License

Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0.
