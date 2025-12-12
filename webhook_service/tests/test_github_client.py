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

"""Tests for GitHub client."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from github_client import GitHubClient


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration."""
    monkeypatch.setenv("GITHUB_APP_ID", "123456")
    monkeypatch.setenv(
        "GITHUB_APP_PRIVATE_KEY",
        "-----BEGIN RSA PRIVATE KEY-----\nMOCK_KEY\n-----END RSA PRIVATE KEY-----",
    )
    Config.GITHUB_APP_ID = "123456"
    Config.GITHUB_APP_PRIVATE_KEY = (
        "-----BEGIN RSA PRIVATE KEY-----\nMOCK_KEY\n-----END RSA PRIVATE KEY-----"
    )


@pytest.fixture
def github_client(mock_config):
    """Create GitHub client with mocked integration."""
    with patch("github_client.GithubIntegration") as mock_integration:
        mock_auth = Mock()
        mock_auth.token = "mock-token"
        mock_integration.return_value.get_access_token.return_value = mock_auth
        client = GitHubClient()
        yield client


def test_get_installation_client(github_client):
    """Test getting installation client."""
    client = github_client.get_installation_client(12345)
    assert client is not None


def test_get_pr_files(github_client):
    """Test getting PR files."""
    # Mock GitHub API responses
    mock_file = Mock()
    mock_file.filename = "test.py"
    mock_file.status = "modified"
    mock_file.additions = 10
    mock_file.deletions = 2
    mock_file.patch = "@@ -1,1 +1,1 @@\n-test\n+test_new"
    mock_file.raw_url = "https://github.com/owner/repo/raw/test.py"

    mock_pr = Mock()
    mock_pr.get_files.return_value = [mock_file]

    mock_repo = Mock()
    mock_repo.get_pull.return_value = mock_pr

    mock_github = Mock()
    mock_github.get_repo.return_value = mock_repo

    with patch.object(
        github_client, "get_installation_client", return_value=mock_github
    ):
        files, pr = github_client.get_pr_files(12345, "owner/repo", 1)

        assert len(files) == 1
        assert files[0]["filename"] == "test.py"
        assert files[0]["status"] == "modified"
        assert files[0]["additions"] == 10
        assert files[0]["deletions"] == 2


def test_get_file_content(github_client):
    """Test getting file content."""
    mock_content = Mock()
    mock_content.decoded_content = b"file content here"

    mock_repo = Mock()
    mock_repo.get_contents.return_value = mock_content

    mock_github = Mock()
    mock_github.get_repo.return_value = mock_repo

    with patch.object(
        github_client, "get_installation_client", return_value=mock_github
    ):
        content = github_client.get_file_content(12345, "owner/repo", "test.py", "main")
        assert content == "file content here"


def test_get_repository_languages(github_client):
    """Test getting repository languages."""
    mock_repo = Mock()
    mock_repo.get_languages.return_value = {"Python": 1000, "TypeScript": 500}

    mock_github = Mock()
    mock_github.get_repo.return_value = mock_repo

    with patch.object(
        github_client, "get_installation_client", return_value=mock_github
    ):
        languages = github_client.get_repository_languages(12345, "owner/repo")
        assert "Python" in languages
        assert "TypeScript" in languages
