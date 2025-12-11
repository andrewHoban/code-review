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

"""Output formatting tools for code review results."""

import logging
from typing import Any, Literal

from google.adk.tools import FunctionTool, ToolContext

from app.models.output_schema import (
    CodeReviewOutput,
    InlineComment,
    ReviewMetrics,
)

logger = logging.getLogger(__name__)


def format_review_output(
    summary: str,
    issues: list[dict[str, Any]],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """
    Formats raw analysis into structured PR review format.

    Args:
        summary: Overall review summary (markdown)
        issues: List of issue dictionaries with file, line, severity, message
        tool_context: ADK tool context

    Returns:
        Dictionary containing formatted CodeReviewOutput
    """
    logger.info("Tool: Formatting review output...")

    try:
        inline_comments = []
        critical_count = 0
        warning_count = 0
        suggestion_count = 0

        for issue in issues:
            severity = issue.get("severity", "info")
            if severity == "error":
                critical_count += 1
            elif severity == "warning":
                warning_count += 1
            elif severity == "suggestion":
                suggestion_count += 1

            inline_comments.append(
                InlineComment(
                    path=issue.get("file", ""),
                    line=issue.get("line", 0),
                    side=issue.get("side", "RIGHT"),
                    body=issue.get("message", ""),
                    severity=severity,
                )
            )

        # Get metrics from state or calculate
        # Calculate files_reviewed: try state first, then count unique files from issues,
        # then use changed_files from state, finally default to 0
        if "files_reviewed" in tool_context.state:
            files_reviewed = tool_context.state["files_reviewed"]
        else:
            # Count unique files from issues
            unique_files = {
                issue.get("file", "") for issue in issues if issue.get("file")
            }
            files_reviewed = len(unique_files)
            # If no issues, try to get from changed_files in state
            if files_reviewed == 0:
                changed_files = tool_context.state.get("changed_files", [])
                if changed_files:
                    files_reviewed = len(changed_files)

        # Get style_score: prefer Python, then TypeScript, default to 0.0
        # Use .get() with None to distinguish between missing key and 0 value
        python_score = tool_context.state.get("python_style_score")
        typescript_score = tool_context.state.get("typescript_style_score")

        if python_score is not None:
            style_score = float(python_score)
        elif typescript_score is not None:
            style_score = float(typescript_score)
        else:
            style_score = 0.0

        metrics = ReviewMetrics(
            files_reviewed=files_reviewed,
            issues_found=len(issues),
            critical_issues=critical_count,
            warnings=warning_count,
            suggestions=suggestion_count,
            style_score=style_score,
        )

        # Determine overall status
        overall_status: Literal["APPROVED", "NEEDS_CHANGES", "COMMENT"]
        if critical_count > 0:
            overall_status = "NEEDS_CHANGES"
        elif warning_count > 0 or len(issues) > 0:
            overall_status = "COMMENT"
        else:
            overall_status = "APPROVED"

        output = CodeReviewOutput(
            summary=summary,
            inline_comments=inline_comments,
            overall_status=overall_status,
            metrics=metrics,
        )

        # Store in state
        tool_context.state["formatted_output"] = output.model_dump()

        logger.info(
            f"Tool: Formatted output - {len(inline_comments)} comments, "
            f"status: {overall_status}"
        )

        return {
            "status": "success",
            "output": output.model_dump(),
            "summary": f"Formatted {len(inline_comments)} comments with status {overall_status}",
        }

    except Exception as e:
        error_msg = f"Output formatting failed: {e!s}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "message": error_msg,
        }


# Export tool
format_review_output_tool = FunctionTool(func=format_review_output)
