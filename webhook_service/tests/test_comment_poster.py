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

"""Tests for comment poster."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from comment_poster import CommentPoster
from github_client import GitHubClient


@pytest.fixture
def mock_github_client():
    """Create mock GitHub client."""
    client = Mock(spec=GitHubClient)

    mock_pr = Mock()
    mock_pr.get_commits.return_value.reversed = [Mock(sha="abc123")]
    mock_pr.head.sha = "abc123"

    mock_repo = Mock()
    mock_repo.get_pull.return_value = mock_pr

    mock_github = Mock()
    mock_github.get_repo.return_value = mock_repo

    client.get_installation_client.return_value = mock_github

    return client


def test_post_review(mock_github_client):
    """Test posting review comments."""
    poster = CommentPoster(mock_github_client)

    review_response = {
        "summary": "## Review Summary\n\nLooks good!",
        "inline_comments": [
            {
                "path": "test.py",
                "line": 10,
                "body": "Good improvement!",
                "severity": "info",
                "side": "RIGHT",
            }
        ],
        "metrics": {
            "files_reviewed": 1,
            "issues_found": 1,
            "critical_issues": 0,
        },
    }

    poster.post_review(
        installation_id=12345,
        repo_full_name="owner/repo",
        pr_number=1,
        review_response=review_response,
    )

    # Verify PR was accessed
    mock_github = mock_github_client.get_installation_client.return_value
    mock_repo = mock_github.get_repo.return_value
    mock_pr = mock_repo.get_pull.return_value

    # Verify comment was posted
    assert mock_pr.create_issue_comment.called
    assert mock_pr.create_review_comment.called


def test_post_review_no_comments(mock_github_client):
    """Test posting review with no inline comments."""
    poster = CommentPoster(mock_github_client)

    review_response = {
        "summary": "## Review Summary\n\nNo issues!",
        "inline_comments": [],
        "metrics": {},
    }

    poster.post_review(
        installation_id=12345,
        repo_full_name="owner/repo",
        pr_number=1,
        review_response=review_response,
    )

    # Should still post summary
    mock_github = mock_github_client.get_installation_client.return_value
    mock_repo = mock_github.get_repo.return_value
    mock_pr = mock_repo.get_pull.return_value

    assert mock_pr.create_issue_comment.called
