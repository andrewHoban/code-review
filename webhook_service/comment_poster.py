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

"""Post review comments to GitHub PR."""

import logging
from typing import Any

from github_client import GitHubClient

logger = logging.getLogger(__name__)


class CommentPoster:
    """Post review comments to GitHub PRs."""

    def __init__(self, github_client: GitHubClient):
        """Initialize comment poster.

        Args:
            github_client: GitHub client instance
        """
        self.github_client = github_client

    def post_review(
        self,
        installation_id: int,
        repo_full_name: str,
        pr_number: int,
        review_response: dict[str, Any],
    ) -> None:
        """Post review as a single PR comment.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number
            review_response: Review response from Agent Engine (must contain markdown_review field)
        """
        try:
            client = self.github_client.get_installation_client(installation_id)
            repo = client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # Get markdown review text
            markdown_review = review_response.get("markdown_review", "")

            if not markdown_review:
                raise ValueError("No markdown_review in response")

            # Post as single comment
            pr.create_issue_comment(markdown_review)
            logger.info("Posted review comment")

        except Exception as e:
            logger.error(f"Error posting review: {e}", exc_info=True)
            raise
