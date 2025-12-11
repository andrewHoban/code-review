# Testing Guidelines for Code Review Agent

This document outlines the comprehensive testing strategy for the multi-language GitHub PR code review agent.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Pyramid](#test-pyramid)
3. [Testing Levels](#testing-levels)
4. [Test Organization](#test-organization)
5. [Writing Tests](#writing-tests)
6. [Test Data Management](#test-data-management)
7. [Coverage Requirements](#coverage-requirements)
8. [Continuous Testing](#continuous-testing)
9. [Performance Testing](#performance-testing)
10. [Integration Testing](#integration-testing)

## Testing Philosophy

Our testing approach follows these principles:

- **Test Early, Test Often**: Write tests alongside code, not after
- **Test in Isolation**: Each test should be independent and repeatable
- **Test Realistic Scenarios**: Use realistic PR data, not contrived examples
- **Fast Feedback**: Unit tests should run in <1 second each
- **Clear Failures**: Test failures should immediately indicate what's wrong

## Test Pyramid

```
        /\
       /E2E\          5% - Full PR review flows
      /------\
     /  INT   \       25% - Pipeline integration tests
    /----------\
   /   UNIT     \     70% - Tool and function tests
  /--------------\
```

### Distribution Rationale

- **70% Unit Tests**: Fast, isolated, catch bugs early
- **25% Integration Tests**: Verify agent orchestration and state flow
- **5% End-to-End Tests**: Validate complete system behavior

## Testing Levels

### 1. Unit Tests (70% of tests)

**Location:** `tests/unit/`

**Purpose:** Test individual functions and tools in isolation

**Characteristics:**
- Fast execution (<1s per test)
- No external dependencies (mocked)
- Test one thing at a time
- High code coverage target (90%+)

**Example Structure:**
```python
# tests/unit/test_python_tools.py
import pytest
from app.tools.python_tools import analyze_python_structure

def test_analyze_python_structure_simple_function():
    """Test AST analysis of a simple Python function."""
    code = """
def add(a, b):
    return a + b
"""
    result = analyze_python_structure(code)

    assert result['functions'] == [{'name': 'add', 'args': ['a', 'b']}]
    assert result['function_count'] == 1
```

**What to Test:**
- Tool functions with various inputs
- Edge cases (empty code, syntax errors, large files)
- Error handling
- State management helpers
- Output formatting functions

**Mocking Strategy:**
- Mock file system operations
- Mock subprocess calls (ESLint, pycodestyle)
- Mock external API calls
- Use fixtures for common test data

### 2. Integration Tests (25% of tests)

**Location:** `tests/integration/`

**Purpose:** Test tool execution, state management, and component integration

**Characteristics:**
- Test tools directly with mocked contexts (no LLM API calls)
- Fast execution (<1s per test)
- Verify state flow between components
- Test error handling and edge cases
- Validate actual behavior, not just existence

**Example Structure:**
```python
# tests/integration/test_python_pipeline.py
import pytest
from unittest.mock import MagicMock
from app.tools.python_tools import analyze_python_structure, PythonStateKeys

@pytest.mark.asyncio
async def test_python_structure_analysis_tool_execution():
    """Test that Python structure analysis tool executes correctly."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = "def add(a, b): return a + b"
    result = await analyze_python_structure(code, tool_context)

    # Validate actual behavior
    assert result["status"] == "success"
    assert result["analysis"]["metrics"]["function_count"] == 1
    assert PythonStateKeys.CODE_TO_REVIEW in tool_context.state
    assert tool_context.state[PythonStateKeys.CODE_LINE_COUNT] == 1
```

**What to Test:**
- Tool execution with various inputs
- State storage and retrieval between tools
- Input preparation and parsing utilities
- Language detection logic
- Error handling (syntax errors, missing data, invalid input)
- Edge cases (empty input, unknown files, malformed data)
- Agent configuration and structure

**Test Data:**
- Use realistic but minimal test data
- Include edge cases (empty inputs, syntax errors, missing files)
- Test both Python and TypeScript scenarios
- Mock external dependencies (no real API calls)

**Important:** Integration tests should NOT make real LLM API calls. Use mocked `ToolContext` objects. Real API tests belong in `tests/e2e/`.

### 3. End-to-End Tests (5% of tests)

**Location:** `tests/e2e/`

**Purpose:** Test complete system with real API calls to LLM models

**Characteristics:**
- Make real API calls to Gemini models (slow - 20+ seconds per test)
- Test full pipeline execution with actual LLM responses
- Validate end-to-end behavior
- Use realistic PR payload examples
- Marked with `@pytest.mark.e2e` and `@pytest.mark.slow`

**Example Structure:**
```python
# tests/e2e/test_real_api_calls.py
import pytest
from app.agent import root_agent
from google.adk.runners import Runner

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_real_python_pr_review():
    """Test complete review of a real Python PR with actual API calls."""
    payload = load_fixture("real_python_pr.json")

    runner = Runner(agent=root_agent)
    result = await runner.run_async(
        new_message=create_message(payload),
        user_id="test_user",
        session_id="test_session"
    )

    # Validate output structure
    output = parse_agent_output(result)
    assert output['overall_status'] in ['APPROVED', 'NEEDS_CHANGES', 'COMMENT']
    assert all('path' in c and 'line' in c for c in output['inline_comments'])
```

**What to Test:**
- Complete PR review flow with real LLM calls
- Multi-file PRs
- PRs with both Python and TypeScript
- Output format compliance
- Real API integration validation

**When to Run:**
- Before major releases
- In CI on main branch (with rate limiting)
- Manually before deployment
- **NOT in regular test runs** - use `pytest -m "not e2e"` to skip

**Running E2E Tests:**
```bash
# Run E2E tests explicitly
pytest -m "e2e" tests/e2e/

# Skip E2E tests (default for fast runs)
pytest -m "not e2e"
```

## Test Organization

### Directory Structure

```
tests/
├── unit/
│   ├── test_python_tools.py
│   ├── test_typescript_tools.py
│   ├── test_language_detection.py
│   ├── test_repo_context.py
│   └── test_output_formatter.py
├── integration/
│   ├── test_python_pipeline.py
│   ├── test_typescript_pipeline.py
│   ├── test_language_routing.py
│   └── test_multi_language.py
├── e2e/
│   ├── test_full_pr_review.py
│   └── test_error_scenarios.py
├── fixtures/
│   ├── python_simple.py
│   ├── typescript_simple.ts
│   ├── real_python_pr.json
│   └── multi_language_pr.json
└── conftest.py  # Shared fixtures
```

### Naming Conventions

- Test files: `test_<module_name>.py`
- Test functions: `test_<functionality>_<scenario>()`
- Fixtures: `fixture_<name>()` or `@pytest.fixture`

### Test Categories

Use pytest markers to categorize tests:

```python
@pytest.mark.unit
@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow  # For tests that take >5 seconds
@pytest.mark.asyncio  # For async tests
```

Run specific categories:
```bash
pytest -m unit  # Only unit tests
pytest -m "not slow"  # Skip slow tests
```

## Writing Tests

### Test Structure (AAA Pattern)

```python
def test_example():
    # Arrange - Set up test data
    code = "def hello(): pass"
    expected_functions = 1

    # Act - Execute the function
    result = analyze_python_structure(code)

    # Assert - Verify results
    assert result['function_count'] == expected_functions
```

### Async Test Pattern

```python
@pytest.mark.asyncio
async def test_async_tool():
    result = await some_async_tool(input_data)
    assert result['status'] == 'success'
```

### Fixtures for Common Data

```python
# tests/conftest.py
import pytest
from app.models.input_schema import CodeReviewInput, ChangedFile

@pytest.fixture
def sample_python_file():
    return ChangedFile(
        path="src/example.py",
        language="python",
        status="modified",
        diff="@@ -1,3 +1,3 @@\n...",
        full_content="def hello():\n    return 'world'",
        lines_changed=[1, 2, 3]
    )

@pytest.fixture
def minimal_pr_input(sample_python_file):
    return CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=1,
            repository="test/repo",
            title="Test PR",
            description="",
            author="test_user",
            base_branch="main",
            head_branch="feature"
        ),
        review_context=ReviewContext(
            changed_files=[sample_python_file],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(...)
        )
    )
```

### Testing Tools with Mocking

```python
from unittest.mock import patch, MagicMock

def test_style_checker_with_mock():
    """Test style checker without actually running pycodestyle."""
    with patch('subprocess.run') as mock_run:
        # Mock pycodestyle output
        mock_run.return_value = MagicMock(
            stdout="src/test.py:5:1: E302 expected 2 blank lines",
            returncode=1
        )

        result = check_python_style("def test(): pass")

        assert result['issue_count'] == 1
        assert result['issues'][0]['line'] == 5
```

## Test Data Management

### Fixture Files

Store realistic test data in `tests/fixtures/`:

- **Code samples**: `python_simple.py`, `typescript_complex.ts`
- **PR payloads**: `real_python_pr.json`, `multi_language_pr.json`
- **Expected outputs**: `expected_review_output.json`

### Generating Test Data

```python
# tests/fixtures/generate_test_data.py
def create_test_pr_payload(languages=['python'], file_count=3):
    """Generate a realistic PR payload for testing."""
    return {
        "pr_metadata": {...},
        "review_context": {
            "changed_files": [create_test_file(lang) for lang in languages],
            ...
        }
    }
```

### Test Data Principles

- **Realistic**: Use real code patterns, not contrived examples
- **Minimal**: Use smallest examples that test the functionality
- **Varied**: Include edge cases (empty, large, malformed)
- **Maintainable**: Update when requirements change

## Coverage Requirements

### Minimum Coverage Targets

- **Overall**: 80% code coverage
- **Tools**: 90% coverage (critical business logic)
- **Agents**: 70% coverage (instruction testing via integration)
- **Models/Schemas**: 100% coverage (data validation)

### Measuring Coverage

```bash
# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

### Coverage Exclusions

Exclude from coverage:
- Type stubs (`*.pyi` files)
- Test files themselves
- Deployment scripts
- Configuration files

```ini
# .coveragerc
[run]
omit =
    */tests/*
    */__pycache__/*
    */venv/*
    setup.py
```

## Continuous Testing

### Pre-Commit Hooks

Run fast tests before commit:
```bash
# .git/hooks/pre-commit
#!/bin/sh
pytest tests/unit -m "not slow" --tb=short
```

### CI Pipeline

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest tests/unit --cov=app
      - name: Run integration tests
        run: pytest tests/integration
      - name: Run E2E tests (main branch only)
        if: github.ref == 'refs/heads/main'
        run: pytest tests/e2e
```

### Test Execution Commands

```bash
# Run all fast tests (unit + integration, excludes E2E)
pytest -m "not e2e"

# Run all tests including E2E (slow!)
pytest

# Run only unit tests
pytest tests/unit

# Run only integration tests (fast, no API calls)
pytest tests/integration

# Run E2E tests (real API calls - slow!)
pytest -m "e2e" tests/e2e/

# Run with coverage
pytest --cov=app --cov-report=term-missing -m "not e2e"

# Run specific test file
pytest tests/unit/test_python_tools.py

# Run specific test
pytest tests/unit/test_python_tools.py::test_analyze_python_structure

# Skip slow tests (includes E2E)
pytest -m "not slow"
```

## Performance Testing

### Latency Targets

- **Unit tests**: <1s per test
- **Integration tests**: <1s per test (no API calls, uses mocks)
- **E2E tests**: 20-60s per test (includes real model API calls)
- **Full PR review**: <60s for typical PR (<10 files)

### Performance Benchmarks

```python
# tests/performance/test_latency.py
import pytest
import time

@pytest.mark.performance
def test_python_pipeline_latency():
    """Ensure Python pipeline completes within target time."""
    start = time.time()
    result = run_python_pipeline(test_input)
    duration = time.time() - start

    assert duration < 30.0, f"Pipeline took {duration}s, target is <30s"
```

### Load Testing

For production deployment, test with:
- Multiple concurrent PR reviews
- Large PRs (50+ files)
- Mixed language PRs
- Error scenarios

## Integration Testing

### Testing Agent Orchestration

```python
@pytest.mark.integration
async def test_language_detection_routing():
    """Test that root agent correctly routes to language pipelines."""
    input_data = create_multi_language_pr(['python', 'typescript'])

    result = await run_agent(root_agent, input_data)

    # Verify both pipelines were invoked
    assert 'python' in result.summary.lower()
    assert 'typescript' in result.summary.lower()
```

### Testing State Flow

```python
@pytest.mark.integration
async def test_state_persistence_across_agents():
    """Verify state flows correctly through pipeline."""
    # Run first agent
    state_after_analyzer = await run_agent(code_analyzer, input_data)

    # Run second agent with same state
    state_after_style = await run_agent(
        style_checker,
        input_data,
        initial_state=state_after_analyzer.state
    )

    # Verify state was preserved
    assert 'code_analysis' in state_after_style.state
```

### Testing Error Handling

```python
@pytest.mark.integration
async def test_pipeline_handles_syntax_errors():
    """Test pipeline gracefully handles syntax errors."""
    input_data = create_pr_with_syntax_error()

    result = await run_pipeline(python_review_pipeline, input_data)

    # Should still produce output, but flag the error
    assert result.overall_status == 'NEEDS_CHANGES'
    assert any('syntax error' in c.body.lower()
               for c in result.inline_comments)
```

## Best Practices

1. **Write tests first** (TDD) for complex logic
2. **Test behavior, not implementation** - Focus on what, not how
3. **Use descriptive test names** - `test_analyze_python_structure_with_nested_classes()` not `test_analyze()`
4. **Keep tests independent** - No shared state between tests
5. **Mock external dependencies** - Don't call real APIs in unit tests
6. **Test edge cases** - Empty inputs, None values, large inputs
7. **Verify error handling** - Test that errors are caught and handled
8. **Document complex tests** - Add docstrings explaining why the test exists

## Troubleshooting

### Common Issues

**Tests pass locally but fail in CI:**
- Check environment differences (Python version, dependencies)
- Verify test data paths are relative, not absolute
- Check for race conditions in async tests

**Slow test execution:**
- Integration tests should be fast (<1s) - if slow, you're likely making real API calls
- Use `pytest -m "not e2e"` to skip E2E tests (which are slow by design)
- Use `pytest -x` to stop on first failure
- Use `pytest --lf` to run only failed tests
- E2E tests are intentionally slow (real API calls) - only run when needed

**Flaky tests:**
- Look for non-deterministic behavior (random, time-based)
- Check for shared state between tests
- Verify async test synchronization

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [ADK Testing Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/testing.html)
