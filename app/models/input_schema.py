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

"""Input schema models for code review agent."""

from pydantic import BaseModel, Field, field_validator

from app.utils.security import (
    MAX_FILE_CONTENT_SIZE,
    sanitize_branch_name,
    sanitize_repository_name,
    validate_commit_sha,
    validate_content_size,
)


class PullRequestMetadata(BaseModel):
    """Metadata about the pull request being reviewed."""

    pr_number: int = Field(..., gt=0, lt=1000000, description="Pull request number")
    repository: str = Field(
        ..., max_length=200, description="Repository full name (owner/repo)"
    )
    title: str = Field(..., max_length=500, description="PR title")
    description: str = Field(default="", max_length=10000, description="PR description")
    author: str = Field(..., max_length=100, description="PR author username")
    base_branch: str = Field(..., max_length=200, description="Base branch name")
    head_branch: str = Field(..., max_length=200, description="Head branch name")
    base_sha: str | None = Field(None, description="Base commit SHA")
    head_sha: str | None = Field(None, description="Head commit SHA")

    @field_validator("repository")
    @classmethod
    def validate_repository(cls, v: str) -> str:
        """Validate and sanitize repository name."""
        return sanitize_repository_name(v)

    @field_validator("base_branch", "head_branch")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        """Validate and sanitize branch name."""
        return sanitize_branch_name(v)

    @field_validator("base_sha", "head_sha")
    @classmethod
    def validate_sha(cls, v: str | None) -> str | None:
        """Validate commit SHA format."""
        if v is not None:
            validate_commit_sha(v)
        return v


class ChangedFile(BaseModel):
    """A file that was changed in the PR."""

    path: str = Field(
        ..., max_length=500, description="File path relative to repo root"
    )
    language: str = Field(
        ..., max_length=50, description="Programming language (python, typescript)"
    )
    status: str = Field(
        ...,
        max_length=20,
        description="Change status (modified, added, deleted, renamed)",
    )
    additions: int = Field(default=0, ge=0, description="Number of lines added")
    deletions: int = Field(default=0, ge=0, description="Number of lines deleted")
    diff: str = Field(
        ..., max_length=MAX_FILE_CONTENT_SIZE, description="Unified diff patch"
    )
    full_content: str = Field(
        default="",
        max_length=MAX_FILE_CONTENT_SIZE,
        description="Complete file content after changes (optional - only include for new files or when diff is insufficient)",
    )
    lines_changed: list[int] = Field(
        default_factory=list, description="Line numbers that were changed"
    )

    @field_validator("full_content", "diff")
    @classmethod
    def validate_content_size(cls, v: str) -> str:
        """Validate content size."""
        validate_content_size(v, MAX_FILE_CONTENT_SIZE)
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        valid_statuses = {"modified", "added", "deleted", "renamed"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v


class RelatedFile(BaseModel):
    """A file related to the changed files (imports, dependencies, etc.)."""

    path: str = Field(
        ..., max_length=500, description="File path relative to repo root"
    )
    content: str = Field(
        ..., max_length=MAX_FILE_CONTENT_SIZE, description="Complete file content"
    )
    relationship: str = Field(
        ...,
        max_length=500,
        description="How this file relates (e.g., 'imported by src/auth.ts')",
    )
    language: str = Field(..., max_length=50, description="Programming language")

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v: str) -> str:
        """Validate content size."""
        validate_content_size(v, MAX_FILE_CONTENT_SIZE)
        return v


class TestFile(BaseModel):
    """A test file associated with changed files."""

    path: str = Field(..., max_length=500, description="Test file path")
    content: str = Field(
        ..., max_length=MAX_FILE_CONTENT_SIZE, description="Complete test file content"
    )
    tests_for: str = Field(
        ..., max_length=500, description="Path of file this test covers"
    )
    language: str = Field(..., max_length=50, description="Programming language")

    @field_validator("content")
    @classmethod
    def validate_content_size(cls, v: str) -> str:
        """Validate content size."""
        validate_content_size(v, MAX_FILE_CONTENT_SIZE)
        return v


class FileDependencies(BaseModel):
    """Dependency information for a file."""

    imports: list[str] = Field(
        default_factory=list, max_length=100, description="Files this file imports"
    )
    imported_by: list[str] = Field(
        default_factory=list, max_length=100, description="Files that import this file"
    )

    @field_validator("imports", "imported_by")
    @classmethod
    def validate_paths(cls, v: list[str]) -> list[str]:
        """Validate path list size and individual paths."""
        if len(v) > 100:
            raise ValueError("Too many dependencies (max 100)")
        for path in v:
            if len(path) > 500:
                raise ValueError(f"Path too long: {path}")
        return v


class RepositoryInfo(BaseModel):
    """Information about the repository."""

    name: str = Field(..., max_length=200, description="Repository name")
    primary_language: str = Field(
        ..., max_length=50, description="Primary programming language"
    )
    languages_used: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="All languages in the repository",
    )
    total_files: int = Field(default=0, ge=0, description="Total number of files")
    has_tests: bool = Field(default=False, description="Whether repository has tests")

    @field_validator("languages_used")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        """Validate languages list size."""
        if len(v) > 50:
            raise ValueError("Too many languages (max 50)")
        return v


class ReviewContext(BaseModel):
    """Complete context for code review including changed files and related context."""

    changed_files: list[ChangedFile] = Field(
        ..., description="Files that were changed in the PR"
    )
    related_files: list[RelatedFile] = Field(
        default_factory=list, description="Files related to changed files"
    )
    test_files: list[TestFile] = Field(
        default_factory=list, description="Test files for changed files"
    )
    dependency_map: dict[str, FileDependencies] = Field(
        default_factory=dict, description="Dependency relationships between files"
    )
    repository_info: RepositoryInfo = Field(
        ..., description="Information about the repository"
    )


class CodeReviewInput(BaseModel):
    """Complete input for code review agent."""

    pr_metadata: PullRequestMetadata = Field(..., description="PR metadata")
    review_context: ReviewContext = Field(..., description="Review context with files")
