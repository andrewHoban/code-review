#!/usr/bin/env python3
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

"""Post code review results as comments on a GitHub PR."""

import argparse
import json
import sys
import time
from typing import Any

from github import Github


def get_severity_emoji(severity: str) -> str:
    """Get emoji for severity level."""
    emoji_map = {
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ",  # noqa: RUF001
        "suggestion": "💡",
    }
    return emoji_map.get(severity, "💬")


def post_pr_comment(github: Github, repository: str, pr_number: int, body: str) -> None:
    """Post a comment on a PR."""
    try:
        repo = github.get_repo(repository)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(body)
        print(f"Posted summary comment on PR #{pr_number}")
    except Exception as e:
        print(f"Error posting PR comment: {e}", file=sys.stderr)
        raise


def post_review_comments(
    github: Github, repository: str, pr_number: int, comments: list[dict[str, Any]]
) -> None:
    """Post inline review comments on a PR."""
    if not comments:
        print("No inline comments to post")
        return

    try:
        repo = github.get_repo(repository)
        pr = repo.get_pull(pr_number)

        # Group comments by file and line
        comments_by_file: dict[str, list[dict[str, Any]]] = {}
        for comment in comments:
            file_path = comment["path"]
            if file_path not in comments_by_file:
                comments_by_file[file_path] = []
            comments_by_file[file_path].append(comment)

        # Post comments for each file
        total_posted = 0
        for file_path, file_comments in comments_by_file.items():
            # Get file SHA
            try:
                file_sha = pr.head.sha
            except Exception:
                print(
                    f"Warning: Could not get SHA for {file_path}, skipping inline comments"
                )
                continue

            # Post each comment
            for comment in file_comments:
                try:
                    # GitHub API expects 'line' for single line comments
                    # For multi-line, we'd need 'start_line' and 'line'
                    line = comment.get("line")
                    if not line:
                        continue

                    body = comment.get("body", "")
                    side = comment.get("side", "RIGHT")

                    # Create review comment
                    pr.create_review_comment(
                        body=body,
                        commit_id=file_sha,
                        path=file_path,
                        line=line,
                        side=side,
                    )

                    total_posted += 1
                    # Rate limiting - GitHub allows 5000 requests/hour, so we can be generous
                    time.sleep(0.1)

                except Exception as e:
                    print(
                        f"Warning: Could not post comment on {file_path}:{line}: {e}",
                        file=sys.stderr,
                    )
                    continue

        print(f"Posted {total_posted} inline review comments")

    except Exception as e:
        print(f"Error posting review comments: {e}", file=sys.stderr)
        # Don't raise - we may have posted some comments successfully


def create_review_with_comments(
    github: Github,
    repository: str,
    pr_number: int,
    summary: str,
    comments: list[dict[str, Any]],
    status: str,
) -> None:
    """Create a review with inline comments and overall status."""
    try:
        repo = github.get_repo(repository)
        pr = repo.get_pull(pr_number)

        # Map our status to GitHub review state
        # APPROVED -> APPROVE
        # NEEDS_CHANGES -> REQUEST_CHANGES
        # COMMENT -> COMMENT
        github_state_map = {
            "APPROVED": "APPROVE",
            "NEEDS_CHANGES": "REQUEST_CHANGES",
            "COMMENT": "COMMENT",
        }
        github_state = github_state_map.get(status, "COMMENT")

        # Build review body
        review_body = f"{summary}\n\n---\n*Automated code review by AI agent*"

        # Group comments by file
        review_comments = []
        for comment in comments:
            file_path = comment["path"]
            line = comment.get("line")
            if not line:
                continue

            review_comments.append(
                {
                    "path": file_path,
                    "position": line,  # GitHub uses position in diff, but line works for most cases
                    "body": comment.get("body", ""),
                }
            )

        # Create review
        if review_comments or github_state != "COMMENT":
            pr.create_review(
                body=review_body,
                event=github_state,
                comments=review_comments,
            )
            print(f"Created review with state: {github_state}")
        else:
            # Just post as comment if no inline comments
            pr.create_issue_comment(review_body)
            print("Posted review as PR comment")

    except Exception as e:
        print(f"Error creating review: {e}", file=sys.stderr)
        # Fallback to posting comments individually
        post_pr_comment(github, repository, pr_number, summary)
        post_review_comments(github, repository, pr_number, comments)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Post code review results to GitHub PR"
    )
    parser.add_argument("--response", required=True, help="Agent response JSON file")
    parser.add_argument(
        "--repository", required=True, help="Repository name (owner/repo)"
    )
    parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    parser.add_argument("--github-token", required=True, help="GitHub token")
    parser.add_argument(
        "--create-review",
        action="store_true",
        help="Create a GitHub review instead of separate comments",
    )

    args = parser.parse_args()

    try:
        # Load response
        with open(args.response) as f:
            response = json.load(f)

        # Initialize GitHub client
        github = Github(args.github_token)

        summary = response.get("summary", "No summary provided")
        inline_comments = response.get("inline_comments", [])
        overall_status = response.get("overall_status", "COMMENT")
        metrics = response.get("metrics", {})

        # Enhance summary with metrics
        if metrics:
            issues_found = metrics.get("issues_found", 0)
            critical_issues = metrics.get("critical_issues", 0)
            files_reviewed = metrics.get("files_reviewed", 0)

            metrics_text = "\n\n**Review Metrics:**\n"
            metrics_text += f"- Files reviewed: {files_reviewed}\n"
            metrics_text += f"- Total issues: {issues_found}\n"
            metrics_text += f"- Critical issues: {critical_issues}\n"

            if "style_score" in metrics:
                metrics_text += f"- Style score: {metrics['style_score']:.1f}/100\n"

            summary = summary + metrics_text

        if args.create_review:
            # Create a single review with all comments
            create_review_with_comments(
                github,
                args.repository,
                args.pr_number,
                summary,
                inline_comments,
                overall_status,
            )
        else:
            # Post summary as PR comment
            post_pr_comment(github, args.repository, args.pr_number, summary)

            # Post inline comments
            if inline_comments:
                post_review_comments(
                    github, args.repository, args.pr_number, inline_comments
                )

        print(f"Successfully posted review for PR #{args.pr_number}")

    except Exception as e:
        print(f"Error posting review: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
