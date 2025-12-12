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

"""GitHub API client for webhook service."""

import logging

from config import Config
from github import Github, GithubIntegration

logger = logging.getLogger(__name__)


class GitHubClient:
    """GitHub API client using GitHub App authentication."""

    def __init__(self):
        """Initialize GitHub client with App credentials."""
        if not Config.GITHUB_APP_ID or not Config.GITHUB_APP_PRIVATE_KEY:
            raise ValueError("GitHub App ID and private key must be configured")
        self.integration = GithubIntegration(
            Config.GITHUB_APP_ID,
            Config.GITHUB_APP_PRIVATE_KEY,
        )

    def get_installation_client(self, installation_id: int) -> Github:
        """Get an authenticated GitHub client for a specific installation.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Authenticated Github client
        """
        auth = self.integration.get_access_token(installation_id)
        return Github(auth.token)

    def get_pr_files(
        self, installation_id: int, repo_full_name: str, pr_number: int
    ) -> tuple[list[dict], object]:
        """Get files changed in a pull request.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number

        Returns:
            Tuple of (changed_files list, PR object)
        """
        client = self.get_installation_client(installation_id)
        repo = client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)

        changed_files = []
        for file in pr.get_files():
            changed_files.append(
                {
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "patch": file.patch or "",
                    "raw_url": file.raw_url,
                }
            )

        return changed_files, pr

    def get_file_content(
        self,
        installation_id: int,
        repo_full_name: str,
        file_path: str,
        ref: str = "main",
    ) -> str:
        """Get file content from repository.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository full name
            file_path: Path to file relative to repo root
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            File content as string
        """
        try:
            client = self.get_installation_client(installation_id)
            repo = client.get_repo(repo_full_name)
            file_content = repo.get_contents(file_path, ref=ref)
            return file_content.decoded_content.decode("utf-8")
        except Exception as e:
            logger.warning(f"Could not get file content for {file_path}: {e}")
            return ""

    def get_repository_languages(
        self, installation_id: int, repo_full_name: str
    ) -> dict[str, int]:
        """Get repository language statistics.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository full name

        Returns:
            Dictionary mapping language names to bytes of code
        """
        try:
            client = self.get_installation_client(installation_id)
            repo = client.get_repo(repo_full_name)
            return repo.get_languages()
        except Exception as e:
            logger.warning(f"Could not get repository languages: {e}")
            return {}
