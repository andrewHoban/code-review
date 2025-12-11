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

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PullRequestMetadata(BaseModel):
    """Metadata about the pull request being reviewed."""

    pr_number: int = Field(..., description="Pull request number")
    repository: str = Field(..., description="Repository full name (owner/repo)")
    title: str = Field(..., description="PR title")
    description: str = Field(default="", description="PR description")
    author: str = Field(..., description="PR author username")
    base_branch: str = Field(..., description="Base branch name")
    head_branch: str = Field(..., description="Head branch name")
    base_sha: Optional[str] = Field(None, description="Base commit SHA")
    head_sha: Optional[str] = Field(None, description="Head commit SHA")


class ChangedFile(BaseModel):
    """A file that was changed in the PR."""

    path: str = Field(..., description="File path relative to repo root")
    language: str = Field(..., description="Programming language (python, typescript)")
    status: str = Field(
        ..., description="Change status (modified, added, deleted, renamed)"
    )
    additions: int = Field(default=0, description="Number of lines added")
    deletions: int = Field(default=0, description="Number of lines deleted")
    diff: str = Field(..., description="Unified diff patch")
    full_content: str = Field(..., description="Complete file content after changes")
    lines_changed: List[int] = Field(
        default_factory=list, description="Line numbers that were changed"
    )


class RelatedFile(BaseModel):
    """A file related to the changed files (imports, dependencies, etc.)."""

    path: str = Field(..., description="File path relative to repo root")
    content: str = Field(..., description="Complete file content")
    relationship: str = Field(
        ...,
        description="How this file relates (e.g., 'imported by src/auth.ts')",
    )
    language: str = Field(..., description="Programming language")


class TestFile(BaseModel):
    """A test file associated with changed files."""

    path: str = Field(..., description="Test file path")
    content: str = Field(..., description="Complete test file content")
    tests_for: str = Field(..., description="Path of file this test covers")
    language: str = Field(..., description="Programming language")


class FileDependencies(BaseModel):
    """Dependency information for a file."""

    imports: List[str] = Field(
        default_factory=list, description="Files this file imports"
    )
    imported_by: List[str] = Field(
        default_factory=list, description="Files that import this file"
    )


class RepositoryInfo(BaseModel):
    """Information about the repository."""

    name: str = Field(..., description="Repository name")
    primary_language: str = Field(..., description="Primary programming language")
    languages_used: List[str] = Field(
        default_factory=list, description="All languages in the repository"
    )
    total_files: int = Field(default=0, description="Total number of files")
    has_tests: bool = Field(default=False, description="Whether repository has tests")


class ReviewContext(BaseModel):
    """Complete context for code review including changed files and related context."""

    changed_files: List[ChangedFile] = Field(
        ..., description="Files that were changed in the PR"
    )
    related_files: List[RelatedFile] = Field(
        default_factory=list, description="Files related to changed files"
    )
    test_files: List[TestFile] = Field(
        default_factory=list, description="Test files for changed files"
    )
    dependency_map: Dict[str, FileDependencies] = Field(
        default_factory=dict, description="Dependency relationships between files"
    )
    repository_info: RepositoryInfo = Field(
        ..., description="Information about the repository"
    )


class CodeReviewInput(BaseModel):
    """Complete input for code review agent."""

    pr_metadata: PullRequestMetadata = Field(..., description="PR metadata")
    review_context: ReviewContext = Field(..., description="Review context with files")
