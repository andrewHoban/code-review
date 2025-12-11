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

"""Security utilities for input validation and sanitization."""

import re
from pathlib import Path

# Maximum sizes for different content types
MAX_FILE_CONTENT_SIZE = 100 * 1024  # 100KB
MAX_CODE_CONTENT_SIZE = 500 * 1024  # 500KB
MAX_JSON_PAYLOAD_SIZE = 10 * 1024 * 1024  # 10MB
MAX_SYMBOL_LENGTH = 200
MAX_PATH_LENGTH = 500


def sanitize_file_path(path: str, repo_root: Path | None = None) -> Path:
    """
    Sanitize and validate a file path to prevent path traversal attacks.

    Args:
        path: File path to sanitize
        repo_root: Optional repository root to validate against

    Returns:
        Normalized Path object

    Raises:
        ValueError: If path is invalid or outside repository root
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Remove null bytes (path traversal attempt)
    if "\0" in path:
        raise ValueError("Path contains null bytes")

    # Remove leading/trailing whitespace
    path = path.strip()

    # Check length
    if len(path) > MAX_PATH_LENGTH:
        raise ValueError(f"Path too long (max {MAX_PATH_LENGTH} characters)")

    # If repo_root provided, resolve relative to it
    if repo_root:
        repo_root_resolved = Path(repo_root).resolve()
        # Join with repo root to handle relative paths correctly
        try:
            # If path is absolute, it should be within repo_root
            if Path(path).is_absolute():
                normalized = Path(path).resolve()
            else:
                # Relative path - join with repo root
                normalized = (repo_root_resolved / path).resolve()

            # Ensure it's within repo root
            if not is_path_within_root(normalized, repo_root_resolved):
                raise ValueError(
                    f"Path outside repository root: {path} (resolved to {normalized})"
                )
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid path: {e}") from e
    else:
        # No repo root - just normalize
        try:
            normalized = Path(path).resolve()
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid path: {e}") from e

    return normalized


def is_path_within_root(path: Path, root: Path) -> bool:
    """
    Check if a path is within the repository root.

    Args:
        path: Path to check
        root: Repository root path

    Returns:
        True if path is within root, False otherwise
    """
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def sanitize_symbol_for_regex(symbol: str) -> str:
    """
    Escape special regex characters in a symbol name to prevent ReDoS attacks.

    Args:
        symbol: Symbol name to sanitize

    Returns:
        Escaped symbol safe for use in regex patterns

    Raises:
        ValueError: If symbol is invalid
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty")

    if len(symbol) > MAX_SYMBOL_LENGTH:
        raise ValueError(f"Symbol too long (max {MAX_SYMBOL_LENGTH} characters)")

    # Remove null bytes
    symbol = symbol.replace("\0", "")

    # Escape regex special characters
    return re.escape(symbol)


def validate_content_size(content: str, max_size: int = MAX_CODE_CONTENT_SIZE) -> None:
    """
    Validate that content size is within limits.

    Args:
        content: Content to validate
        max_size: Maximum allowed size in bytes

    Raises:
        ValueError: If content exceeds maximum size
    """
    if not isinstance(content, str):
        raise TypeError("Content must be a string")

    content_size = len(content.encode("utf-8"))
    if content_size > max_size:
        raise ValueError(
            f"Content too large: {content_size} bytes (max {max_size} bytes)"
        )


def validate_commit_sha(sha: str) -> None:
    """
    Validate that a commit SHA has a valid format.

    Args:
        sha: Commit SHA to validate

    Raises:
        ValueError: If SHA format is invalid
    """
    if not sha:
        raise ValueError("Commit SHA cannot be empty")

    # Git SHAs are 40 hex characters (or 7+ for short SHAs)
    if not re.match(r"^[0-9a-f]{7,40}$", sha, re.IGNORECASE):
        raise ValueError(f"Invalid commit SHA format: {sha}")


def sanitize_repository_name(repo_name: str) -> str:
    """
    Validate and sanitize a repository name.

    Args:
        repo_name: Repository name in format 'owner/repo'

    Returns:
        Sanitized repository name

    Raises:
        ValueError: If repository name format is invalid
    """
    if not repo_name:
        raise ValueError("Repository name cannot be empty")

    if len(repo_name) > 200:
        raise ValueError("Repository name too long (max 200 characters)")

    # Check format: owner/repo
    if "/" not in repo_name:
        raise ValueError("Repository name must be in format 'owner/repo'")

    parts = repo_name.split("/")
    if len(parts) != 2:
        raise ValueError("Repository name must have exactly one '/' separator")

    owner, repo = parts

    # Validate owner and repo names
    # GitHub allows: alphanumeric, hyphens, underscores, dots
    if not re.match(r"^[a-zA-Z0-9._-]+$", owner):
        raise ValueError(f"Invalid owner name: {owner}")

    if not re.match(r"^[a-zA-Z0-9._-]+$", repo):
        raise ValueError(f"Invalid repository name: {repo}")

    # Check for path traversal attempts
    if ".." in repo_name or repo_name.startswith("/"):
        raise ValueError("Repository name contains invalid characters")

    return repo_name


def sanitize_branch_name(branch: str) -> str:
    """
    Validate and sanitize a branch name.

    Args:
        branch: Branch name to validate

    Returns:
        Sanitized branch name

    Raises:
        ValueError: If branch name is invalid
    """
    if not branch:
        raise ValueError("Branch name cannot be empty")

    if len(branch) > 200:
        raise ValueError("Branch name too long (max 200 characters)")

    # Remove null bytes
    branch = branch.replace("\0", "")

    # Check for path traversal
    if ".." in branch or branch.startswith("/"):
        raise ValueError("Branch name contains invalid characters")

    # Git branch names can't contain certain characters
    invalid_chars = ["~", "^", ":", "?", "*", "[", " ", "..", "@{"]
    for char in invalid_chars:
        if char in branch:
            raise ValueError(f"Branch name contains invalid character: {char}")

    return branch
