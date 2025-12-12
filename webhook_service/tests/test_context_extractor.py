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

"""Tests for context extractor."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from context_extractor import detect_language, extract_review_context, is_test_file
from github_client import GitHubClient


@pytest.fixture
def mock_github_client():
    """Create mock GitHub client."""
    client = Mock(spec=GitHubClient)

    # Mock PR files
    mock_file = Mock()
    mock_file.filename = "src/test.py"
    mock_file.status = "modified"
    mock_file.additions = 10
    mock_file.deletions = 2
    mock_file.patch = "@@ -1,1 +1,1 @@\n-old\n+new"
    mock_file.raw_url = "https://github.com/owner/repo/raw/test.py"

    mock_pr = Mock()
    mock_pr.number = 1
    mock_pr.title = "Test PR"
    mock_pr.body = "Test description"
    mock_pr.user.login = "testuser"
    mock_pr.base.ref = "main"
    mock_pr.head.ref = "feature"
    mock_pr.base.sha = "abc123"
    mock_pr.head.sha = "def456"
    mock_pr.get_files.return_value = [mock_file]

    client.get_pr_files.return_value = (
        [
            {
                "filename": "src/test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 2,
                "patch": "@@ -1,1 +1,1 @@\n-old\n+new",
                "raw_url": "https://github.com/owner/repo/raw/test.py",
            }
        ],
        mock_pr,
    )

    client.get_repository_languages.return_value = {"Python": 1000}

    return client


def test_detect_language():
    """Test language detection."""
    assert detect_language("test.py") == "python"
    assert detect_language("test.ts") == "typescript"
    assert detect_language("test.js") == "javascript"
    assert detect_language("test.txt") is None


def test_is_test_file():
    """Test test file detection."""
    assert is_test_file("test_file.py", "python") is True
    assert is_test_file("test_file_test.py", "python") is True
    assert is_test_file("file.py", "python") is False
    assert is_test_file("file.test.ts", "typescript") is True


def test_extract_review_context(mock_github_client):
    """Test context extraction."""
    pr_data = {
        "number": 1,
        "title": "Test PR",
        "body": "Test description",
        "user": {"login": "testuser"},
        "base": {"ref": "main", "sha": "abc123"},
        "head": {"ref": "feature", "sha": "def456"},
    }

    context = extract_review_context(
        installation_id=12345,
        repo_full_name="owner/repo",
        pr_number=1,
        pr_data=pr_data,
        github_client=mock_github_client,
    )

    assert "pr_metadata" in context
    assert "review_context" in context
    assert context["pr_metadata"]["pr_number"] == 1
    assert context["pr_metadata"]["repository"] == "owner/repo"
    assert len(context["review_context"]["changed_files"]) == 1
    assert context["review_context"]["changed_files"][0]["path"] == "src/test.py"


def test_extract_review_context_no_supported_files(mock_github_client):
    """Test context extraction with no supported files."""
    # Mock client to return no Python/TypeScript files
    mock_github_client.get_pr_files.return_value = (
        [
            {
                "filename": "README.md",
                "status": "modified",
                "additions": 1,
                "deletions": 1,
                "patch": "",
                "raw_url": "",
            }
        ],
        Mock(),
    )

    pr_data = {
        "number": 1,
        "title": "Test PR",
        "body": "",
        "user": {"login": "testuser"},
        "base": {"ref": "main", "sha": "abc123"},
        "head": {"ref": "feature", "sha": "def456"},
    }

    with pytest.raises(ValueError, match="No supported files"):
        extract_review_context(
            installation_id=12345,
            repo_full_name="owner/repo",
            pr_number=1,
            pr_data=pr_data,
            github_client=mock_github_client,
        )
