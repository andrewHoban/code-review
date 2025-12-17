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

"""Tests for structured output schema validation."""

import json

from app.models.output_schema import CodeReviewOutput, InlineComment, ReviewMetrics


def test_code_review_output_schema() -> None:
    """Test that CodeReviewOutput validates correct structure."""
    valid_output = {
        "summary": "LGTM - no significant issues.",
        "overall_status": "APPROVED",
        "inline_comments": [],
        "metrics": {
            "files_reviewed": 3,
            "issues_found": 0,
            "critical_issues": 0,
            "warnings": 0,
            "suggestions": 0,
        },
    }

    output = CodeReviewOutput.model_validate(valid_output)
    assert output.summary == "LGTM - no significant issues."
    assert output.overall_status == "APPROVED"
    assert len(output.inline_comments) == 0
    assert output.metrics.files_reviewed == 3


def test_code_review_output_with_comments() -> None:
    """Test CodeReviewOutput with inline comments."""
    output_data = {
        "summary": "Found 2 issues that need attention.",
        "overall_status": "NEEDS_CHANGES",
        "inline_comments": [
            {
                "path": "src/auth.py",
                "line": 42,
                "severity": "error",
                "body": "SQL injection vulnerability - use parameterized queries",
            },
            {
                "path": "src/utils.py",
                "line": 15,
                "severity": "warning",
                "body": "Consider adding error handling for this API call",
            },
        ],
        "metrics": {
            "files_reviewed": 2,
            "issues_found": 2,
            "critical_issues": 1,
            "warnings": 1,
            "suggestions": 0,
        },
    }

    output = CodeReviewOutput.model_validate(output_data)
    assert output.overall_status == "NEEDS_CHANGES"
    assert len(output.inline_comments) == 2
    assert output.inline_comments[0].severity == "error"
    assert output.metrics.critical_issues == 1


def test_review_metrics_no_style_score() -> None:
    """Test that ReviewMetrics works without deprecated style_score field."""
    metrics_data = {
        "files_reviewed": 5,
        "issues_found": 3,
        "critical_issues": 1,
        "warnings": 2,
        "suggestions": 0,
    }

    metrics = ReviewMetrics.model_validate(metrics_data)
    assert metrics.files_reviewed == 5
    assert metrics.issues_found == 3
    # Verify style_score is not required
    assert not hasattr(metrics, "style_score") or metrics.style_score == 0.0


def test_json_serialization() -> None:
    """Test that models can be serialized to JSON."""
    output = CodeReviewOutput(
        summary="Test review",
        overall_status="COMMENT",
        inline_comments=[
            InlineComment(
                path="test.py",
                line=1,
                severity="info",
                body="Test comment",
            )
        ],
        metrics=ReviewMetrics(
            files_reviewed=1,
            issues_found=1,
            critical_issues=0,
            warnings=0,
            suggestions=1,
        ),
    )

    # Serialize to JSON
    json_str = output.model_dump_json()
    data = json.loads(json_str)

    # Verify structure
    assert "summary" in data
    assert "overall_status" in data
    assert "inline_comments" in data
    assert "metrics" in data
    assert len(data["inline_comments"]) == 1


def test_invalid_status_rejected() -> None:
    """Test that invalid overall_status values are rejected."""
    import pytest
    from pydantic import ValidationError

    invalid_output = {
        "summary": "Test",
        "overall_status": "INVALID_STATUS",  # Not in allowed values
        "inline_comments": [],
        "metrics": {
            "files_reviewed": 1,
            "issues_found": 0,
            "critical_issues": 0,
            "warnings": 0,
            "suggestions": 0,
        },
    }

    with pytest.raises(ValidationError):
        CodeReviewOutput.model_validate(invalid_output)


def test_invalid_severity_rejected() -> None:
    """Test that invalid severity values are rejected."""
    import pytest
    from pydantic import ValidationError

    invalid_comment = {
        "path": "test.py",
        "line": 1,
        "severity": "invalid",  # Not in allowed values
        "body": "Test",
    }

    with pytest.raises(ValidationError):
        InlineComment.model_validate(invalid_comment)
