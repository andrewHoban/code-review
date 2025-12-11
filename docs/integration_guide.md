# Integration Guide for GitHub PR Code Review Agent

This guide is for engineers integrating the code review agent with GitHub Actions or other CI/CD systems.

## Overview

The code review agent accepts structured JSON input containing PR metadata and review context, and returns structured JSON output with review comments and feedback.

## Input Contract

### Endpoint

The agent is deployed as an ADK Agent Engine instance. Call it via the Agent Engine API:

```
POST https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/reasoningEngines/{engine_id}:query
```

### Request Format

The agent expects a JSON payload in the user message:

```json
{
  "pr_metadata": {
    "pr_number": 123,
    "repository": "owner/repo",
    "title": "Fix authentication bug",
    "description": "Fixes issue with user authentication",
    "author": "username",
    "base_branch": "main",
    "head_branch": "feature/auth-fix",
    "base_sha": "abc123...",
    "head_sha": "def456..."
  },
  "review_context": {
    "changed_files": [
      {
        "path": "src/auth.ts",
        "language": "typescript",
        "status": "modified",
        "additions": 15,
        "deletions": 3,
        "diff": "@@ -10,7 +10,7 @@\n-const user = data;\n+const user = await validateUser(data);\n",
        "full_content": "export async function authenticate(user: User): Promise<boolean> {\n  return await validateUser(user);\n}",
        "lines_changed": [10, 11, 12]
      }
    ],
    "related_files": [
      {
        "path": "src/validation.ts",
        "content": "export async function validateUser(user: User): Promise<boolean> { ... }",
        "relationship": "imported by src/auth.ts",
        "language": "typescript"
      }
    ],
    "test_files": [
      {
        "path": "tests/auth.test.ts",
        "content": "describe('authenticate', () => { ... })",
        "tests_for": "src/auth.ts",
        "language": "typescript"
      }
    ],
    "dependency_map": {
      "src/auth.ts": {
        "imports": ["src/validation.ts"],
        "imported_by": ["src/api/auth-routes.ts"]
      }
    },
    "repository_info": {
      "name": "repo",
      "primary_language": "typescript",
      "languages_used": ["typescript", "python"],
      "total_files": 150,
      "has_tests": true
    }
  }
}
```

### Required Fields

**pr_metadata:**
- `pr_number` (int): Pull request number
- `repository` (string): Full repository name (owner/repo)
- `title` (string): PR title
- `author` (string): PR author username
- `base_branch` (string): Base branch name
- `head_branch` (string): Head branch name

**review_context:**
- `changed_files` (array): At least one changed file
- `repository_info` (object): Repository metadata

### Optional Fields

- `description`: PR description (defaults to empty string)
- `base_sha`, `head_sha`: Commit SHAs
- `related_files`: Files related to changed files (imports, dependencies)
- `test_files`: Test files for changed files
- `dependency_map`: Dependency relationships

## Output Contract

### Response Format

The agent returns a JSON object with this structure:

```json
{
  "summary": "## Code Review Summary\n\nOverall assessment...",
  "inline_comments": [
    {
      "path": "src/auth.ts",
      "line": 10,
      "side": "RIGHT",
      "body": "⚠️ **Security Issue**: Direct user data access without validation...",
      "severity": "error"
    },
    {
      "path": "src/auth.ts",
      "line": 15,
      "side": "RIGHT",
      "body": "💡 **Suggestion**: Consider adding error handling here...",
      "severity": "suggestion"
    }
  ],
  "overall_status": "NEEDS_CHANGES",
  "metrics": {
    "files_reviewed": 3,
    "issues_found": 7,
    "critical_issues": 2,
    "warnings": 3,
    "suggestions": 2,
    "style_score": 85.5
  }
}
```

### Field Descriptions

**summary** (string): Markdown-formatted overall review summary

**inline_comments** (array): Comments for specific lines
- `path`: File path relative to repo root
- `line`: Line number (1-indexed)
- `side`: "LEFT" (old code) or "RIGHT" (new code)
- `body`: Comment text (markdown)
- `severity`: "error", "warning", "info", or "suggestion"

**overall_status** (string): One of:
- `"APPROVED"`: No issues found
- `"NEEDS_CHANGES"`: Critical issues require fixes
- `"COMMENT"`: Non-blocking feedback provided

**metrics** (object): Review statistics
- `files_reviewed`: Number of files analyzed
- `issues_found`: Total issues
- `critical_issues`: Number of error-level issues
- `warnings`: Number of warning-level issues
- `suggestions`: Number of suggestion-level issues
- `style_score`: Style compliance score (0-100)

## GitHub Actions Integration

### Automated PR Reviews

The repository includes a ready-to-use GitHub Actions workflow that automatically reviews PRs.

**Workflow:** `.github/workflows/pr-review.yml`

This workflow:
- Triggers on PR events (opened, synchronize, reopened)
- Extracts review context from changed files
- Calls the deployed agent via Agent Engine API
- Posts review comments and summary on the PR

**Prerequisites:**
- GitHub Secrets configured:
  - `GCP_PROJECT_ID`: Your GCP project ID
  - `GCP_PROJECT_NUMBER`: Your GCP project number
  - `GCP_REGION`: GCP region (e.g., `europe-west1`)
- Workload Identity Federation configured for GCP authentication

**How it works:**
1. When a PR is opened or updated, the workflow runs
2. `extract_review_context.py` builds the agent input payload from PR data
3. `call_agent.py` invokes the deployed Agent Engine
4. `post_review.py` posts the agent's feedback as PR comments

### Using in Other Repositories

To use the code review agent in other repositories, use the reusable workflow:

```yaml
name: Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  review:
    uses: owner/code-review/.github/workflows/pr-review-reusable.yml@main
    with:
      project_id: "your-gcp-project-id"
      location: "europe-west1"
      agent_engine_id: "3659508948773371904"
    secrets:
      GCP_PROJECT_NUMBER: ${{ secrets.GCP_PROJECT_NUMBER }}
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Scripts

The integration uses three Python scripts:

**`scripts/extract_review_context.py`**
- Extracts PR metadata from GitHub API
- Gets changed files using `git diff`
- Finds related files (imports, dependencies)
- Finds test files
- Builds JSON payload matching agent input schema

**`scripts/call_agent.py`**
- Loads JSON payload
- Authenticates with Google Cloud
- Calls Agent Engine API with retry logic
- Saves agent response as JSON

**`scripts/post_review.py`**
- Loads agent response
- Posts summary as PR comment
- Posts inline comments on specific lines
- Optionally creates a GitHub review with status

## Error Handling

### Common Errors

**Invalid JSON format:**
- Response: `{"status": "error", "message": "Invalid JSON format: ..."}`
- Solution: Validate JSON before sending

**No supported languages:**
- Response: `{"status": "error", "message": "No supported languages detected"}`
- Solution: Check file extensions match supported languages

**Agent timeout:**
- Response: HTTP 504 or timeout error
- Solution: Increase timeout, reduce file count, or split into multiple reviews

### Retry Strategy

For transient errors:
1. Retry with exponential backoff (3 attempts)
2. Log errors for monitoring
3. Fall back to manual review if all retries fail

## Performance Considerations

### Latency Targets

- **Small PRs** (<5 files): <30 seconds
- **Medium PRs** (5-15 files): <60 seconds
- **Large PRs** (>15 files): <120 seconds

### Optimization Tips

1. **Limit file count**: Review max 20 files per PR
2. **Cache results**: Cache reviews for unchanged files
3. **Parallel processing**: Process multiple files concurrently
4. **Skip unchanged**: Only review files with actual changes

## Security Considerations

1. **Authentication**: Use service account with minimal permissions
2. **Input validation**: Validate all input before sending to agent
3. **Output sanitization**: Sanitize output before posting to GitHub
4. **Rate limiting**: Implement rate limiting to prevent abuse
5. **Secrets management**: Store credentials in GitHub Secrets

## Testing

### Test Payloads

See `tests/fixtures/` for example payloads:
- `python_simple_pr.json`: Simple Python PR
- `typescript_complex_pr.json`: Complex TypeScript PR
- `multi_language_pr.json`: PR with both Python and TypeScript

### Local Testing

```bash
# Test with example payload
python scripts/call_agent.py \
  --payload=tests/fixtures/python_simple_pr.json \
  --output=test_response.json
```

## Support

For issues or questions:
1. Check logs in Cloud Trace
2. Review agent output for error messages
3. Contact the agent development team
