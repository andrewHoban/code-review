# Integration Test Refactoring Summary

## Problem

The integration tests were making **real API calls to Gemini models**, causing:
- **Very slow test execution** (40-80+ seconds per test)
- **Minimal assertions** - only checking that keys exist, not validating behavior
- **Rate limiting issues** in CI
- **Poor test quality** - tests that can't fail

## Solution

Refactored all integration tests to:
1. **Test tools directly** with mocked contexts (no LLM calls)
2. **Test state management** and data flow between components
3. **Add meaningful assertions** that validate actual behavior
4. **Move real API tests** to separate E2E test file with proper markers

## What Changed

### 1. `tests/integration/test_python_pipeline.py`
**Before:** Made 4-6 real API calls per test, only checked state keys exist

**After:**
- Tests tool execution directly with mocked contexts
- Validates analysis results (function count, class count, etc.)
- Tests state storage and retrieval
- Tests error handling (syntax errors, missing code)
- Tests input preparation utilities
- **Runs in < 1 second per test**

### 2. `tests/integration/test_language_routing.py`
**Before:** Made 5-8 real API calls per test, only checked state keys exist

**After:**
- Tests language detection tool directly
- Validates detection results (languages found, file mappings)
- Tests edge cases (unknown files, empty input, missing paths)
- Tests integration with input preparation
- Tests multiple language extensions (.py, .pyi, .ts, .tsx)
- **Runs in < 1 second per test**

### 3. `tests/integration/test_agent.py`
**Before:** Made real API calls (was skipped)

**After:**
- Tests agent configuration and structure
- Validates agent has correct tools and sub-agents
- Tests pipeline structure (sequential agents, sub-agents)
- No API calls - pure configuration testing
- **Runs in < 1 second per test**

### 4. `tests/integration/test_agent_engine_app.py`
**Before:** Made real API calls (was skipped)

**After:**
- Tests feedback registration with valid/invalid inputs
- Tests error handling for invalid feedback
- Tests agent app configuration
- E2E test moved to separate file
- **Runs in < 1 second per test**

### 5. `tests/e2e/test_real_api_calls.py` (NEW)
**Purpose:** Contains all tests that make real API calls

**Tests:**
- Python pipeline E2E with real API calls
- Root agent language routing with real API calls
- Agent stream functionality

**Markers:**
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests
- `@pytest.mark.skip` - Tests that should be run manually

## Running Tests

### Run all fast integration tests (default):
```bash
pytest tests/integration/
```

### Run only unit tests:
```bash
pytest tests/unit/
```

### Run only integration tests (no E2E):
```bash
pytest -m "not e2e"
```

### Run E2E tests (real API calls):
```bash
pytest -m "e2e" tests/e2e/
```

### Skip slow tests:
```bash
pytest -m "not slow"
```

## Test Performance

**Before:**
- Integration tests: 40-80+ seconds total
- Each test: 20+ seconds (multiple API calls)

**After:**
- Integration tests: < 5 seconds total
- Each test: < 1 second (no API calls)
- E2E tests: Only run when needed (manual/CI)

## Test Quality Improvements

### Before (Bad):
```python
assert len(events) > 0  # Just checking we got SOME response
assert "python_structure_analysis_summary" in final_state  # Checking key exists
assert isinstance(analysis, str)  # Checking it's a string
assert len(analysis) > 0  # Checking it's not empty
```

### After (Good):
```python
# Verify tool execution
assert result["status"] == "success"
assert result["analysis"]["metrics"]["function_count"] == 2  # Validates actual count
assert result["analysis"]["classes"][0]["name"] == "Calculator"  # Validates content

# Verify state storage
assert PythonStateKeys.CODE_TO_REVIEW in tool_context.state
assert tool_context.state[PythonStateKeys.CODE_LINE_COUNT] == 7  # Validates value
```

## Key Principles

1. **Test behavior, not implementation** - Validate what the code does, not how
2. **Mock external dependencies** - Don't make real API calls in integration tests
3. **Test edge cases** - Empty input, errors, missing data
4. **Validate state flow** - Test that data flows correctly between components
5. **Fast feedback** - Tests should run quickly for rapid development

## Migration Guide

If you need to add new integration tests:

1. **Test tools directly** with mocked `ToolContext`
2. **Test state management** - verify data is stored/retrieved correctly
3. **Test error handling** - verify graceful failures
4. **Use meaningful assertions** - validate actual values, not just existence
5. **Only use E2E tests** for validating real API integration (rarely needed)

Example:
```python
@pytest.mark.asyncio
async def test_my_tool_execution():
    """Test that my tool executes correctly."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = await my_tool("input", tool_context)

    # Validate behavior
    assert result["status"] == "success"
    assert result["data"]["count"] == 5  # Actual value
    assert "my_state_key" in tool_context.state
    assert tool_context.state["my_state_key"] == "expected_value"
```
