# Code Review Agent

A demo multi-language code review agent for GitHub PRs, built with Google's Agent Development Kit (ADK).

## Overview

This agent analyzes pull requests and provides structured feedback for Python and TypeScript code. It uses an **orchestrator pattern** with a multi-agent pipeline architecture:
- **Orchestrator Agent**: Detects languages and routes to specialized pipelines
- **Language Pipelines**: Sequential agents for code analysis, design checking, test analysis, and feedback synthesis
- **Publisher Agent**: Formats final output as structured JSON for GitHub integration

## Features

- **Multi-Language Support**: Python and TypeScript with extensible architecture
- **Repository Context**: Analyzes related files and dependencies
- **Structured Output**: JSON format ready for GitHub API integration
- **Model Optimization**: Uses appropriate Gemini models for each task
- **Production Ready**: Deployed to Agent Engine with observability
- **Automated PR Reviews**: Automatically reviews PRs and posts comments via GitHub Actions

## Architecture

The agent uses an **orchestrator pattern** with a clear separation of concerns:

```
Root Agent (SequentialAgent)
  │
  ├─ Orchestrator Agent (CodeReviewOrchestrator)
  │   ├─ Language Detection Tool
  │   ├─ Repository Context Tools
  │   │
  │   ├─ Python Review Pipeline (Sequential)
  │   │   ├─ Code Analyzer (gemini-2.5-pro)
  │   │   ├─ Design Checker (gemini-2.5-pro)
  │   │   ├─ Test Analyzer (gemini-2.5-pro)
  │   │   └─ Feedback Synthesizer (gemini-2.5-pro)
  │   │
  │   └─ TypeScript Review Pipeline (Sequential)
  │       ├─ Code Analyzer (gemini-2.5-pro)
  │       ├─ Design Checker (gemini-2.5-pro)
  │       ├─ Test Analyzer (gemini-2.5-pro)
  │       └─ Feedback Synthesizer (gemini-2.5-pro)
  │
  └─ Publisher Agent (ReviewPublisher)
      └─ Formats final JSON output for GitHub
```

**Execution Flow:**
1. **Orchestrator Agent** receives PR context, detects languages, and delegates to appropriate pipelines
2. **Language Pipelines** execute sequentially (Analyzer → Design → Test → Feedback)
3. **Publisher Agent** synthesizes results from all pipelines into a single JSON output

This pattern separates routing logic (orchestrator) from output formatting (publisher), making the system more maintainable and allowing independent optimization of each component.

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
├── tools/           # Analysis tools
├── agents/          # Review pipelines (Python/TypeScript)
├── utils/           # Helper utilities
├── app_utils/       # Deployment and telemetry utilities
├── config.py        # Configuration
├── agent.py         # Orchestrator, publisher, and root agent definitions
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

### Automated Deployment

Pushes to the `main` branch automatically deploy to Agent Engine via GitHub Actions.

**Prerequisites:**
- GCP Workload Identity Federation configured
- GitHub repository secrets set (GCP_PROJECT_ID, GCP_PROJECT_NUMBER, GCP_REGION)

**Deployment Process:**
1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit
3. Push and create PR: `git push -u origin feature/my-feature`
4. Wait for CI tests to pass
5. Merge PR to `main`
6. GitHub Actions automatically deploys to Agent Engine

### Manual Deployment

For testing or one-off deployments:

```bash
# Validate before deploying
make test-deploy

# Deploy to Agent Engine
make deploy
```

### Pre-Deployment Validation

Before pushing code, git hooks automatically run:
- Unit tests (tests/unit)
- Integration tests (tests/integration)
- Pre-deployment checks (make test-deploy)

**To run manually:**
```bash
pytest tests/unit tests/integration -v
make test-deploy
```

See [.cursor/rules/deployment.mdc](.cursor/rules/deployment.mdc) for complete deployment guidelines.

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

- [Testing Guidelines](docs/testing-guidelines.md) - Comprehensive testing strategy
- [Integration Guide](docs/integration_guide.md) - GitHub Actions integration
- [Implementation Status](IMPLEMENTATION_STATUS.md) - Current implementation status
- [Deployment Info](DEPLOYMENT_INFO.md) - Deployment details and access
- [Test Results](TEST_RESULTS.md) - Latest test execution results
- [Next Steps](NEXT_STEPS.md) - Future enhancements and improvements

## License

Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0.
