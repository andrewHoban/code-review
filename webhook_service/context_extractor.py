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

"""Extract review context from GitHub PR using GitHub API."""

import re
import sys
from pathlib import Path

# Add parent directory to path to import app models
sys.path.insert(0, str(Path(__file__).parent.parent))

from github_client import GitHubClient

from app.models.input_schema import (
    ChangedFile,
    CodeReviewInput,
    PullRequestMetadata,
    RepositoryInfo,
    ReviewContext,
)
from app.utils.security import MAX_FILE_CONTENT_SIZE

# Language detection patterns
LANGUAGE_PATTERNS = {
    "python": [r"\.py$", r"\.pyi$"],
    "typescript": [r"\.ts$", r"\.tsx$"],
    "javascript": [r"\.js$", r"\.jsx$"],
}

# Test file patterns
TEST_PATTERNS = {
    "python": [r"test_.*\.py$", r".*_test\.py$", r".*tests?/.*\.py$"],
    "typescript": [r".*\.test\.tsx?$", r".*\.spec\.tsx?$", r".*tests?/.*\.tsx?$"],
    "javascript": [r".*\.test\.jsx?$", r".*\.spec\.jsx?$", r".*tests?/.*\.jsx?$"],
}


def detect_language(file_path: str) -> str | None:
    """Detect programming language from file path."""
    for lang, patterns in LANGUAGE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return lang
    return None


def is_test_file(file_path: str, language: str | None) -> bool:
    """Check if a file is a test file."""
    if not language:
        return False
    patterns = TEST_PATTERNS.get(language, [])
    for pattern in patterns:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    return False


def get_changed_lines(diff: str) -> list[int]:
    """Extract changed line numbers from diff."""
    lines = []
    current_line = 0
    for line in diff.split("\n"):
        if line.startswith("@@"):
            # Parse hunk header: @@ -start,count +start,count @@
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            lines.append(current_line)
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            # Don't increment for deleted lines
            pass
        elif not line.startswith("\\"):
            current_line += 1
    return lines


def extract_review_context(
    installation_id: int,
    repo_full_name: str,
    pr_number: int,
    pr_data: dict,
    github_client: GitHubClient,
) -> dict:
    """Extract review context from a GitHub PR.

    Args:
        installation_id: GitHub App installation ID
        repo_full_name: Repository full name (owner/repo)
        pr_number: Pull request number
        pr_data: PR data from webhook payload
        github_client: GitHub client instance

    Returns:
        Dictionary matching the CodeReviewInput schema
    """
    # Get PR files and metadata
    changed_files_data, pr = github_client.get_pr_files(
        installation_id, repo_full_name, pr_number
    )

    # Build PR metadata
    pr_metadata = PullRequestMetadata(
        pr_number=pr.number,
        repository=repo_full_name,
        title=pr.title or "",
        description=pr.body or "",
        author=pr.user.login if pr.user else "",
        base_branch=pr.base.ref,
        head_branch=pr.head.ref,
        base_sha=pr.base.sha,
        head_sha=pr.head.sha,
    )

    # Process changed files
    processed_files = []
    head_sha = pr.head.sha

    for file_data in changed_files_data:
        file_path = file_data["filename"]
        status_char = file_data["status"]

        # Skip binary and large files
        if file_data.get("additions", 0) + file_data.get("deletions", 0) > 1000:
            continue

        language = detect_language(file_path)
        if not language or language not in ["python", "typescript"]:
            continue

        # Get diff
        diff = file_data.get("patch", "") or ""
        if len(diff) > MAX_FILE_CONTENT_SIZE:
            diff = diff[:MAX_FILE_CONTENT_SIZE]

        lines_changed = get_changed_lines(diff)

        # Determine status
        status_map = {
            "added": "added",
            "removed": "deleted",
            "renamed": "renamed",
            "modified": "modified",
        }
        status = status_map.get(status_char.lower(), "modified")

        # Get full content for new files or major refactors
        full_content = ""
        if status == "added":
            try:
                full_content = github_client.get_file_content(
                    installation_id, repo_full_name, file_path, head_sha
                )
                if len(full_content) > MAX_FILE_CONTENT_SIZE:
                    full_content = full_content[:MAX_FILE_CONTENT_SIZE]
            except Exception:
                pass
        elif diff and len(diff) > 5000:  # Major refactor
            try:
                full_content = github_client.get_file_content(
                    installation_id, repo_full_name, file_path, head_sha
                )
                if len(full_content) > MAX_FILE_CONTENT_SIZE:
                    full_content = full_content[:MAX_FILE_CONTENT_SIZE]
            except Exception:
                pass

        changed_file = ChangedFile(
            path=file_path,
            language=language,
            status=status,
            additions=file_data.get("additions", 0),
            deletions=file_data.get("deletions", 0),
            diff=diff,
            full_content=full_content,
            lines_changed=lines_changed,
        )
        processed_files.append(changed_file)

    if not processed_files:
        raise ValueError("No supported files found in PR")

    # Get repository info
    languages = github_client.get_repository_languages(installation_id, repo_full_name)
    primary_language = (
        "python"
        if "Python" in languages
        else ("TypeScript" if "TypeScript" in languages else "unknown")
    )

    repo_info = RepositoryInfo(
        name=repo_full_name.split("/")[-1],
        primary_language=primary_language.lower(),
        languages_used=list(languages.keys())[:10],
        total_files=0,  # Would need to count via API
        has_tests=True,  # Assume true, would need to check
    )

    # Build review context (simplified - related files and test files would need more API calls)
    review_context = ReviewContext(
        changed_files=processed_files,
        related_files=[],  # Would need to parse imports and fetch files
        test_files=[],  # Would need to search for test files
        dependency_map={},
        repository_info=repo_info,
    )

    return CodeReviewInput(
        pr_metadata=pr_metadata, review_context=review_context
    ).model_dump()
