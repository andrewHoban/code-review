# Code Review Scripts

This directory contains scripts for integrating the code review agent with GitHub PRs.

## Scripts

### `extract_review_context.py`

Extracts review context from a GitHub PR and builds the agent input payload.

**Usage:**
```bash
python scripts/extract_review_context.py \
  --repo-path="/path/to/repo" \
  --pr-number=123 \
  --repository="owner/repo" \
  --base-sha="abc123..." \
  --head-sha="def456..." \
  --github-token="ghp_..." \
  --output=review_payload.json
```

**What it does:**
- Fetches PR metadata from GitHub API
- Gets changed files using `git diff`
- Extracts file contents and diffs
- Finds related files (imports, dependencies)
- Finds test files
- Builds dependency maps
- Generates JSON payload matching agent input schema

**Limitations:**
- Only processes Python and TypeScript files
- Skips files larger than 100KB
- Limits related files to 5 per changed file
- Limits test files to 3 per changed file

### `call_agent.py`

Calls the deployed code review agent via Agent Engine API.

**Usage:**
```bash
python scripts/call_agent.py \
  --payload=review_payload.json \
  --output=review_response.json \
  --project-id="bpc-askgreg-nonprod" \
  --location="europe-west1" \
  --agent-engine-id="3659508948773371904" \
  --max-retries=3
```

**What it does:**
- Loads JSON payload
- Authenticates with Google Cloud (uses Application Default Credentials)
- Calls Agent Engine API
- Handles retries with exponential backoff
- Saves agent response as JSON

**Error Handling:**
- Retries up to 3 times with exponential backoff
- Handles timeout and API errors gracefully

### `post_review.py`

Posts code review results as comments on a GitHub PR.

**Usage:**
```bash
python scripts/post_review.py \
  --response=review_response.json \
  --repository="owner/repo" \
  --pr-number=123 \
  --github-token="ghp_..." \
  --create-review
```

**What it does:**
- Loads agent response JSON
- Posts summary as PR comment
- Posts inline comments on specific lines
- Optionally creates a GitHub review with status (APPROVE/REQUEST_CHANGES/COMMENT)

**Options:**
- `--create-review`: Creates a single GitHub review instead of separate comments
- Without this flag, posts summary as comment and inline comments separately

## Local Testing

### Test with fixture data

```bash
# Extract context from a real PR
python scripts/extract_review_context.py \
  --repo-path="." \
  --pr-number=1 \
  --repository="owner/repo" \
  --base-sha="main" \
  --head-sha="feature-branch" \
  --output=test_payload.json

# Call agent
python scripts/call_agent.py \
  --payload=test_payload.json \
  --output=test_response.json \
  --project-id="your-project" \
  --location="your-region" \
  --agent-engine-id="your-engine-id"

# Post review (dry-run by checking output)
cat test_response.json
```

### Test with fixture files

```bash
# Use existing test fixtures
python scripts/call_agent.py \
  --payload=tests/fixtures/python_simple_pr.json \
  --output=test_response.json \
  --project-id="bpc-askgreg-nonprod" \
  --location="europe-west1" \
  --agent-engine-id="3659508948773371904"
```

## Dependencies

These scripts require:
- `PyGithub` - For GitHub API interactions
- `GitPython` - For git operations
- `google-cloud-aiplatform` - For Agent Engine API
- `pydantic` - For data validation (via app models)

All dependencies are included in `pyproject.toml`.

## Authentication

### GitHub
- Uses `GITHUB_TOKEN` environment variable or `--github-token` argument
- In GitHub Actions, `GITHUB_TOKEN` is automatically provided

### Google Cloud
- Uses Application Default Credentials (ADC)
- In GitHub Actions, uses Workload Identity Federation
- Locally, use `gcloud auth application-default login`

## Error Handling

All scripts include error handling:
- **extract_review_context.py**: Skips unsupported files, handles missing files gracefully
- **call_agent.py**: Retries with exponential backoff, handles API errors
- **post_review.py**: Handles rate limits, continues on partial failures

## Performance Considerations

- **File size limits**: Files >100KB are skipped
- **Rate limiting**: Scripts include delays for GitHub API
- **Batch operations**: Comments are posted with small delays to avoid rate limits

## Troubleshooting

### "No supported files found"
- PR only contains files in unsupported languages
- All files are too large (>100KB)
- Solution: Check file extensions and sizes

### "Agent timeout"
- Large PRs may timeout
- Solution: Reduce number of files or increase timeout in agent config

### "GitHub API rate limit"
- Too many API calls
- Solution: Scripts include rate limiting, but may need to wait

### "Authentication failed"
- GCP credentials not set up
- Solution: Run `gcloud auth application-default login` or check Workload Identity setup
