# Code Review Agent

A production-ready multi-language code review agent for GitHub PRs, built with Google's Agent Development Kit (ADK).

## Overview

This agent analyzes pull requests and provides structured feedback for Python and TypeScript code. It uses a multi-agent pipeline architecture with specialized agents for code analysis, style checking, test analysis, and feedback synthesis.

## Features

- **Multi-Language Support**: Python and TypeScript with extensible architecture
- **Repository Context**: Analyzes related files and dependencies
- **Structured Output**: JSON format ready for GitHub API integration
- **Model Optimization**: Uses appropriate Gemini models for each task
- **Production Ready**: Deployed to Agent Engine with observability

## Architecture

```
Root Agent (gemini-3-pro-preview)
  ├─ Language Detection Tool
  ├─ Repository Context Tools
  │
  ├─ Python Review Pipeline (Sequential)
  │   ├─ Code Analyzer (gemini-3-pro-preview)
  │   ├─ Style Checker (gemini-2.5-flash)
  │   ├─ Test Analyzer (gemini-3-pro-preview)
  │   └─ Feedback Synthesizer (gemini-2.5-pro)
  │
  └─ TypeScript Review Pipeline (Sequential)
      ├─ Code Analyzer (gemini-3-pro-preview)
      ├─ Style Checker (gemini-2.5-flash)
      ├─ Test Analyzer (gemini-3-pro-preview)
      └─ Feedback Synthesizer (gemini-2.5-pro)
```

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
make test
```

## Usage

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
├── agents/          # Review pipelines
├── utils/           # Helper utilities
└── agent.py         # Root orchestrator

tests/
├── unit/            # Unit tests
├── integration/     # Integration tests
└── fixtures/        # Test data

docs/
├── testing-guidelines.md
└── integration_guide.md
```

## Testing

See [`docs/testing-guidelines.md`](docs/testing-guidelines.md) for comprehensive testing documentation.

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit

# Run with coverage
pytest --cov=app --cov-report=html
```

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
