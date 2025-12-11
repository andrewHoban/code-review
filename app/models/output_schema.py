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


class PerformanceMetrics(BaseModel):
    """SWE-bench style performance metrics for the code review."""

    review_duration_seconds: float = Field(
        default=0.0, description="Total time taken for review in seconds"
    )
    tokens_used: int = Field(
        default=0, description="Total tokens used (input + output)"
    )
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens generated")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    agents_used: int = Field(default=0, description="Number of agents involved")
    tool_calls: int = Field(default=0, description="Total tool calls made")
    chunks_received: int = Field(
        default=0, description="Number of stream chunks received"
    )


class ModelUsageInfo(BaseModel):
    """Information about which models were used during the review."""

    agents: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Model usage by agent name",
    )
    fallbacks_used: list[str] = Field(
        default_factory=list,
        description="List of agents that used fallback models",
    )
    used_fallback: bool = Field(
        default=False,
        description="Whether any fallback models were used",
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
    model_usage: ModelUsageInfo = Field(
        default_factory=lambda: ModelUsageInfo(),
        description="Information about which models were used",
    )
    performance: PerformanceMetrics = Field(
        default_factory=lambda: PerformanceMetrics(),
        description="SWE-bench style performance metrics",
    )
