# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration tests for Python review pipeline tools and state management."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.models.input_schema import (
    ChangedFile,
    CodeReviewInput,
    PullRequestMetadata,
    RepositoryInfo,
    ReviewContext,
)
from app.tools.python_tools import (
    PythonStateKeys,
    analyze_python_structure,
    check_python_style,
)
from app.utils.input_preparation import (
    parse_review_input,
    prepare_changed_files_for_detection,
    store_review_context_in_state,
)


@pytest.fixture
def sample_python_code() -> str:
    """Sample Python code for testing."""
    return """def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
"""


@pytest.fixture
def minimal_python_pr_input(sample_python_code: str) -> CodeReviewInput:
    """Minimal PR input for Python review."""
    return CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=1,
            repository="test/repo",
            title="Test PR",
            description="Test description",
            author="test_user",
            base_branch="main",
            head_branch="feature",
        ),
        review_context=ReviewContext(
            changed_files=[
                ChangedFile(
                    path="src/calc.py",
                    language="python",
                    status="added",
                    additions=10,
                    deletions=0,
                    diff="@@ -0,0 +1,10 @@\n" + sample_python_code,
                    full_content=sample_python_code,
                    lines_changed=list(range(1, 11)),
                )
            ],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(
                name="repo",
                primary_language="python",
                languages_used=["python"],
                total_files=10,
                has_tests=False,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_python_structure_analysis_tool_execution(
    sample_python_code: str,
) -> None:
    """Test that Python structure analysis tool executes correctly and stores state."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = await analyze_python_structure(sample_python_code, tool_context)

    # Verify tool execution
    assert result["status"] == "success"
    assert "analysis" in result
    assert "summary" in result

    # Verify analysis content
    analysis = result["analysis"]
    assert analysis["metrics"]["function_count"] == 2  # add + multiply
    assert analysis["metrics"]["class_count"] == 1  # Calculator
    assert len(analysis["functions"]) == 2
    assert len(analysis["classes"]) == 1
    assert analysis["classes"][0]["name"] == "Calculator"
    assert analysis["classes"][0]["methods"] == ["multiply"]

    # Verify state storage
    assert PythonStateKeys.CODE_TO_REVIEW in tool_context.state
    assert PythonStateKeys.CODE_ANALYSIS in tool_context.state
    assert PythonStateKeys.CODE_LINE_COUNT in tool_context.state
    assert tool_context.state[PythonStateKeys.CODE_TO_REVIEW] == sample_python_code
    assert tool_context.state[PythonStateKeys.CODE_LINE_COUNT] == 7


@pytest.mark.asyncio
async def test_python_structure_analysis_retrieves_from_state() -> None:
    """Test that structure analysis retrieves code from state when not provided."""
    tool_context = MagicMock()
    tool_context.state = {
        PythonStateKeys.CODE_TO_REVIEW: "def test(): pass",
    }

    result = await analyze_python_structure("", tool_context)

    assert result["status"] == "success"
    assert result["analysis"]["metrics"]["function_count"] == 1


@pytest.mark.asyncio
async def test_python_structure_analysis_handles_syntax_errors() -> None:
    """Test that structure analysis handles syntax errors gracefully."""
    tool_context = MagicMock()
    tool_context.state = {}

    invalid_code = "def broken(\n    return  # Missing closing paren"
    result = await analyze_python_structure(invalid_code, tool_context)

    assert result["status"] == "error"
    assert "syntax error" in result["message"].lower()
    assert "syntax_error" in result
    assert "line" in result["syntax_error"]


@pytest.mark.asyncio
async def test_python_style_check_tool_execution(sample_python_code: str) -> None:
    """Test that Python style check tool executes correctly and stores state."""
    tool_context = MagicMock()
    tool_context.state = {
        PythonStateKeys.CODE_TO_REVIEW: sample_python_code,
    }

    result = await check_python_style("", tool_context)

    # Verify tool execution
    assert result["status"] == "success"
    assert "score" in result
    assert "issue_count" in result
    assert "issues" in result
    assert isinstance(result["score"], int | float)
    assert 0 <= result["score"] <= 100

    # Verify state storage
    assert PythonStateKeys.STYLE_SCORE in tool_context.state
    assert PythonStateKeys.STYLE_ISSUES in tool_context.state
    assert PythonStateKeys.STYLE_ISSUE_COUNT in tool_context.state
    assert tool_context.state[PythonStateKeys.STYLE_SCORE] == result["score"]


@pytest.mark.asyncio
async def test_python_style_check_retrieves_from_state() -> None:
    """Test that style check retrieves code from state when not provided."""
    tool_context = MagicMock()
    tool_context.state = {
        PythonStateKeys.CODE_TO_REVIEW: "def test(): pass",
    }

    result = await check_python_style("", tool_context)

    assert result["status"] == "success"
    assert "score" in result


@pytest.mark.asyncio
async def test_python_style_check_handles_missing_code() -> None:
    """Test that style check handles missing code gracefully."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = await check_python_style("", tool_context)

    assert result["status"] == "error"
    assert "No Python code" in result["message"]


def test_input_preparation_parse_review_input(
    minimal_python_pr_input: CodeReviewInput,
) -> None:
    """Test parsing review input from JSON string."""
    input_json = minimal_python_pr_input.model_dump_json()
    parsed = parse_review_input(input_json)

    assert parsed.pr_metadata.pr_number == 1
    assert parsed.pr_metadata.repository == "test/repo"
    assert len(parsed.review_context.changed_files) == 1
    assert parsed.review_context.changed_files[0].path == "src/calc.py"


def test_input_preparation_parse_review_input_with_wrapper() -> None:
    """Test parsing review input when JSON is wrapped in text."""
    json_data = '{"pr_metadata": {"pr_number": 1, "repository": "test/repo", "title": "Test", "author": "user", "base_branch": "main", "head_branch": "feature"}, "review_context": {"changed_files": [], "related_files": [], "test_files": [], "dependency_map": {}, "repository_info": {"name": "repo", "primary_language": "python", "languages_used": ["python"], "total_files": 1, "has_tests": false}}}'
    wrapped = f"Here is the payload: {json_data}"

    parsed = parse_review_input(wrapped)
    assert parsed.pr_metadata.pr_number == 1


def test_input_preparation_prepare_changed_files(
    minimal_python_pr_input: CodeReviewInput,
) -> None:
    """Test preparing changed files for language detection."""
    files = prepare_changed_files_for_detection(minimal_python_pr_input)

    assert len(files) == 1
    assert files[0]["path"] == "src/calc.py"
    assert files[0]["status"] == "added"
    assert files[0]["language"] == "python"


def test_input_preparation_store_review_context(
    minimal_python_pr_input: CodeReviewInput,
) -> None:
    """Test storing review context in state."""
    state: dict[str, Any] = {}
    store_review_context_in_state(minimal_python_pr_input, state)

    # Verify all context is stored
    assert "review_context" in state
    assert "pr_metadata" in state
    assert "changed_files" in state
    assert "related_files" in state
    assert "test_files" in state
    assert "dependency_map" in state

    # Verify changed files
    assert len(state["changed_files"]) == 1
    assert state["changed_files"][0]["path"] == "src/calc.py"

    # Verify PR metadata
    assert state["pr_metadata"]["pr_number"] == 1
    assert state["pr_metadata"]["repository"] == "test/repo"


@pytest.mark.asyncio
async def test_python_tools_state_flow() -> None:
    """Test that tools correctly pass state between each other."""
    code = "def hello(): pass"
    tool_context = MagicMock()
    tool_context.state = {}

    # First, analyze structure
    structure_result = await analyze_python_structure(code, tool_context)
    assert structure_result["status"] == "success"
    assert PythonStateKeys.CODE_TO_REVIEW in tool_context.state

    # Then, check style (should use code from state)
    style_result = await check_python_style("", tool_context)
    assert style_result["status"] == "success"
    # Verify it used the same code
    assert tool_context.state[PythonStateKeys.CODE_TO_REVIEW] == code


def test_input_preparation_handles_invalid_json() -> None:
    """Test that input preparation handles invalid JSON gracefully."""
    with pytest.raises(ValueError, match=r"Invalid JSON|No JSON"):
        parse_review_input("not json at all")


def test_input_preparation_handles_empty_input() -> None:
    """Test that input preparation handles empty input gracefully."""
    with pytest.raises(ValueError):
        parse_review_input("")
