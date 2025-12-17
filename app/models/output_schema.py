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

"""Output schema models for code review agent."""

from typing import Literal

from pydantic import BaseModel, Field


class SimpleReviewOutput(BaseModel):
    """Minimal output schema - single markdown field."""

    markdown_review: str = Field(
        ...,
        description="Complete code review in markdown format. Include all sections, findings, and recommendations in this single field.",
    )


class InlineComment(BaseModel):
    """A comment to post on a specific line in a file."""

    path: str = Field(..., description="File path relative to repo root")
    line: int = Field(..., description="Line number to comment on")
    side: Literal["LEFT", "RIGHT"] = Field(
        default="RIGHT", description="Which side of diff (LEFT=old, RIGHT=new)"
    )
    body: str = Field(..., description="Comment body (markdown)")
    severity: Literal["error", "warning", "info", "suggestion"] = Field(
        default="info", description="Comment severity level"
    )


class ReviewMetrics(BaseModel):
    """Metrics about the code review."""

    files_reviewed: int = Field(..., description="Number of files reviewed")
    issues_found: int = Field(..., description="Total issues found")
    critical_issues: int = Field(default=0, description="Critical issues count")
    warnings: int = Field(default=0, description="Warning count")
    suggestions: int = Field(default=0, description="Suggestion count")
    style_score: float = Field(
        default=0.0, description="Style compliance score (0-100)"
    )


class CodeReviewOutput(BaseModel):
    """Complete output from code review agent."""

    summary: str = Field(..., description="Overall review summary in markdown format")
    inline_comments: list[InlineComment] = Field(
        default_factory=list, description="Comments for specific lines"
    )
    overall_status: Literal["APPROVED", "NEEDS_CHANGES", "COMMENT"] = Field(
        ..., description="Overall review status"
    )
    metrics: ReviewMetrics = Field(..., description="Review metrics")
