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
import time
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
    ):
        """Post review comments to GitHub PR.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository full name (owner/repo)
            pr_number: Pull request number
            review_response: Review response from Agent Engine
        """
        try:
            client = self.github_client.get_installation_client(installation_id)
            repo = client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)

            # Post summary comment
            summary = review_response.get("summary", "")
            if summary:
                # Enhance summary with metrics
                metrics = review_response.get("metrics", {})
                if metrics:
                    issues_found = metrics.get("issues_found", 0)
                    critical_issues = metrics.get("critical_issues", 0)
                    files_reviewed = metrics.get("files_reviewed", 0)

                    metrics_text = "\n\n**Review Metrics:**\n"
                    metrics_text += f"- Files reviewed: {files_reviewed}\n"
                    metrics_text += f"- Total issues: {issues_found}\n"
                    metrics_text += f"- Critical issues: {critical_issues}\n"

                    if "style_score" in metrics:
                        metrics_text += (
                            f"- Style score: {metrics['style_score']:.1f}/100\n"
                        )

                    summary = summary + metrics_text

                pr.create_issue_comment(summary)
                logger.info("Posted summary comment")

            # Post inline comments
            inline_comments = review_response.get("inline_comments", [])
            if inline_comments:
                # Get latest commit SHA
                commits = pr.get_commits()
                commit_sha = None
                try:
                    commit_sha = commits.reversed[0].sha
                except (IndexError, AttributeError):
                    commit_sha = pr.head.sha

                total_posted = 0
                for comment in inline_comments:
                    try:
                        file_path = comment.get("path")
                        line = comment.get("line")
                        body = comment.get("body", "")
                        side = comment.get("side", "RIGHT")

                        if not file_path or not line:
                            continue

                        pr.create_review_comment(
                            body=body,
                            commit_id=commit_sha,
                            path=file_path,
                            line=line,
                            side=side,
                        )

                        total_posted += 1
                        # Rate limiting
                        time.sleep(0.1)

                    except Exception as e:
                        logger.warning(
                            f"Could not post comment on {comment.get('path')}:{comment.get('line')}: {e}"
                        )
                        continue

                logger.info(f"Posted {total_posted} inline review comments")

        except Exception as e:
            logger.error(f"Error posting review comments: {e}", exc_info=True)
            raise
