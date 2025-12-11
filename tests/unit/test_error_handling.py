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

"""Unit tests for error handling in code review tools."""

from unittest.mock import MagicMock, patch

import pytest

from app.tools.language_detection import detect_languages
from app.tools.python_tools import analyze_python_structure
from app.tools.typescript_tools import check_typescript_style
from app.utils.input_preparation import parse_review_input


@pytest.mark.asyncio
async def test_analyze_python_structure_empty_code() -> None:
    """Test handling of empty code string."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = await analyze_python_structure("", tool_context)

    assert result["status"] == "error"
    assert "No Python code provided" in result["message"]


@pytest.mark.asyncio
async def test_analyze_python_structure_no_code_in_state() -> None:
    """Test handling when no code is provided and not in state."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = await analyze_python_structure("", tool_context)

    assert result["status"] == "error"
    assert "No Python code provided" in result["message"]


@pytest.mark.asyncio
async def test_analyze_python_structure_syntax_error() -> None:
    """Test handling of Python syntax errors."""
    tool_context = MagicMock()
    tool_context.state = {}

    # Invalid Python syntax
    invalid_code = "def broken(\n    return 42  # Missing closing paren and colon"

    result = await analyze_python_structure(invalid_code, tool_context)

    assert result["status"] == "error"
    assert "syntax error" in result["message"].lower()
    assert "syntax_error" in result
    assert "line" in result["syntax_error"]


def test_detect_languages_empty_list() -> None:
    """Test language detection with empty file list."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = detect_languages([], tool_context)

    assert result["status"] == "success"
    assert result["languages"] == []
    assert result["language_files"] == {}


def test_detect_languages_invalid_file_path() -> None:
    """Test language detection with invalid file paths."""
    tool_context = MagicMock()
    tool_context.state = {}

    # File with missing path key
    changed_files = [{"status": "modified"}]  # Missing 'path' key

    result = detect_languages(changed_files, tool_context)

    # Should not fail, just skip invalid entries
    assert result["status"] == "success"
    assert len(result["languages"]) == 0


def test_detect_languages_none_path() -> None:
    """Test language detection with None path."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = [{"path": None, "status": "modified"}]

    result = detect_languages(changed_files, tool_context)

    # Should handle None gracefully
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_check_typescript_style_empty_code() -> None:
    """Test TypeScript style check with empty code."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = await check_typescript_style("", tool_context)

    assert result["status"] == "error"
    assert "No TypeScript code provided" in result["message"]


@pytest.mark.asyncio
async def test_check_typescript_style_no_code_in_state() -> None:
    """Test TypeScript style check when no code in state."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = await check_typescript_style("", tool_context)

    assert result["status"] == "error"
    assert "No TypeScript code provided" in result["message"]


@pytest.mark.asyncio
async def test_check_typescript_style_subprocess_timeout() -> None:
    """Test TypeScript style check handles subprocess timeout."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = "const x = 1;"

    with patch("app.tools.typescript_tools.subprocess.run") as mock_run:
        from subprocess import TimeoutExpired

        # Simulate timeout
        mock_run.side_effect = TimeoutExpired(["npx", "eslint"], 10)

        result = await check_typescript_style(code, tool_context)

        # Should fall back to pattern-based checking
        assert result["status"] == "success"
        assert "score" in result


def test_parse_review_input_empty_string() -> None:
    """Test parsing empty input string."""
    with pytest.raises(ValueError, match="No JSON object found"):
        parse_review_input("")


def test_parse_review_input_invalid_json() -> None:
    """Test parsing invalid JSON."""
    invalid_json = "{ invalid json }"

    with pytest.raises(ValueError, match="Invalid JSON format"):
        parse_review_input(invalid_json)


def test_parse_review_input_malformed_json() -> None:
    """Test parsing malformed JSON."""
    malformed = '{"pr_metadata": {invalid}'

    with pytest.raises(ValueError):
        parse_review_input(malformed)


def test_parse_review_input_no_json_object() -> None:
    """Test parsing text with no JSON object."""
    text_only = "This is just plain text with no JSON"

    with pytest.raises(ValueError, match="No JSON object found"):
        parse_review_input(text_only)


def test_parse_review_input_incomplete_json() -> None:
    """Test parsing incomplete JSON (missing closing brace)."""
    incomplete = '{"pr_metadata": {"pr_number": 1}'

    with pytest.raises(ValueError):
        parse_review_input(incomplete)
