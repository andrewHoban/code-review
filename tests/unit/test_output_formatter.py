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

"""Unit tests for output formatter."""

import pytest
from unittest.mock import MagicMock

from app.tools.output_formatter import format_review_output


def test_format_review_output_with_critical_issues():
    """Test output formatting with critical issues."""
    tool_context = MagicMock()
    tool_context.state = {"python_style_score": 85.0}

    summary = "Test summary"
    issues = [
        {
            "file": "test.py",
            "line": 10,
            "severity": "error",
            "message": "Critical issue found",
            "side": "RIGHT",
        },
        {
            "file": "test.py",
            "line": 20,
            "severity": "warning",
            "message": "Warning issue",
            "side": "RIGHT",
        },
    ]

    result = format_review_output(summary, issues, tool_context)

    assert result["status"] == "success"
    assert "output" in result
    output = result["output"]
    assert output["overall_status"] == "NEEDS_CHANGES"
    assert output["metrics"]["critical_issues"] == 1
    assert output["metrics"]["warnings"] == 1
    assert output["metrics"]["issues_found"] == 2
    assert len(output["inline_comments"]) == 2


def test_format_review_output_with_warnings_only():
    """Test output formatting with warnings only."""
    tool_context = MagicMock()
    tool_context.state = {"typescript_style_score": 90.0}

    summary = "Test summary"
    issues = [
        {
            "file": "test.ts",
            "line": 15,
            "severity": "warning",
            "message": "Style warning",
            "side": "RIGHT",
        },
    ]

    result = format_review_output(summary, issues, tool_context)

    assert result["status"] == "success"
    output = result["output"]
    assert output["overall_status"] == "COMMENT"
    assert output["metrics"]["critical_issues"] == 0
    assert output["metrics"]["warnings"] == 1


def test_format_review_output_approved():
    """Test output formatting with no issues (approved)."""
    tool_context = MagicMock()
    tool_context.state = {"python_style_score": 100.0}

    summary = "All good!"
    issues = []

    result = format_review_output(summary, issues, tool_context)

    assert result["status"] == "success"
    output = result["output"]
    assert output["overall_status"] == "APPROVED"
    assert output["metrics"]["issues_found"] == 0
    assert output["metrics"]["critical_issues"] == 0


def test_format_review_output_with_suggestions():
    """Test output formatting with suggestions."""
    tool_context = MagicMock()
    tool_context.state = {}

    summary = "Test summary"
    issues = [
        {
            "file": "test.py",
            "line": 5,
            "severity": "suggestion",
            "message": "Consider refactoring",
            "side": "RIGHT",
        },
    ]

    result = format_review_output(summary, issues, tool_context)

    assert result["status"] == "success"
    output = result["output"]
    assert output["metrics"]["suggestions"] == 1
    assert output["overall_status"] == "COMMENT"


def test_format_review_output_style_score_from_state():
    """Test that style score is retrieved from state."""
    tool_context = MagicMock()
    tool_context.state = {"python_style_score": 75.5}

    summary = "Test"
    issues = []

    result = format_review_output(summary, issues, tool_context)

    assert result["status"] == "success"
    output = result["output"]
    assert output["metrics"]["style_score"] == 75.5


def test_format_review_output_files_reviewed_from_state():
    """Test that files_reviewed uses state value when available."""
    tool_context = MagicMock()
    tool_context.state = {"files_reviewed": 5}

    summary = "Test"
    issues = [{"file": "test.py", "line": 1, "severity": "info", "message": "Test"}]

    result = format_review_output(summary, issues, tool_context)

    assert result["status"] == "success"
    output = result["output"]
    assert output["metrics"]["files_reviewed"] == 5


def test_format_review_output_default_severity():
    """Test that default severity is 'info' when not specified."""
    tool_context = MagicMock()
    tool_context.state = {}

    summary = "Test"
    issues = [
        {
            "file": "test.py",
            "line": 1,
            "message": "Test message",
            # No severity specified
        }
    ]

    result = format_review_output(summary, issues, tool_context)

    assert result["status"] == "success"
    output = result["output"]
    assert output["inline_comments"][0]["severity"] == "info"


def test_format_review_output_stores_in_state():
    """Test that formatted output is stored in state."""
    tool_context = MagicMock()
    tool_context.state = {}

    summary = "Test"
    issues = []

    format_review_output(summary, issues, tool_context)

    assert "formatted_output" in tool_context.state
    assert tool_context.state["formatted_output"]["overall_status"] == "APPROVED"
