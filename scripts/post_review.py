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
                        commit=file_sha,
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
        model_usage = response.get("model_usage", {})

        # Enhance summary with metrics (only if not already present and metrics exist)
        if metrics and "**Review Metrics:**" not in summary:
            issues_found = metrics.get("issues_found", 0)
            critical_issues = metrics.get("critical_issues", 0)
            files_reviewed = metrics.get("files_reviewed", 0)
            style_score = metrics.get("style_score", 0.0)

            # Always add metrics section if metrics dict exists (even if values are 0)
            metrics_text = "\n\n**Review Metrics:**\n"
            metrics_text += f"- Files reviewed: {files_reviewed}\n"
            metrics_text += f"- Total issues: {issues_found}\n"
            metrics_text += f"- Critical issues: {critical_issues}\n"

            if "style_score" in metrics:
                metrics_text += f"- Style score: {style_score:.1f}/100\n"

            summary = summary + metrics_text

        # Add model information section
        if model_usage and "**Model Information:**" not in summary:
            model_text = "\n\n**Model Information:**\n"

            agents_info = model_usage.get("agents", {})
            fallbacks_used = model_usage.get("fallbacks_used", [])
            used_fallback = model_usage.get("used_fallback", False)

            if agents_info:
                # Group agents by model type for clarity
                primary_agents = []
                fallback_agents = []

                for agent_name, agent_models in sorted(agents_info.items()):
                    primary = agent_models.get("primary", "Unknown")
                    fallback = agent_models.get("fallback", "")
                    used = agent_models.get("used", primary)

                    if used_fallback and fallback and used == fallback:
                        fallback_agents.append((agent_name, used, primary))
                    else:
                        primary_agents.append((agent_name, used))

                # Show primary model usage first
                if primary_agents:
                    for agent_name, model in primary_agents:
                        model_text += f"- **{agent_name}**: {model}\n"

                # Show fallback usage with warning
                if fallback_agents:
                    model_text += "\n"
                    for agent_name, fallback_model, primary_model in fallback_agents:
                        model_text += f"- **{agent_name}**: {fallback_model} ⚠️ (fallback from {primary_model})\n"

                # Add summary statistics
                total_agents = len(agents_info)
                if used_fallback:
                    model_text += f"\n📊 **Statistics**: {total_agents} agent(s) used, {len(fallback_agents)} used fallback models\n"
                    model_text += "⚠️ **Note**: Some agents used fallback models due to token/quota limits. Review quality may be slightly reduced.\n"
                else:
                    model_text += f"\n📊 **Statistics**: {total_agents} agent(s) used, all with primary models\n"
            else:
                # Fallback: try to get from model_fallbacks if available
                if fallbacks_used:
                    model_text += "- Models used:\n"
                    for fallback_info in fallbacks_used:
                        model_text += f"  - {fallback_info}\n"
                    model_text += "\n⚠️ **Note**: Fallback models were used due to token/quota limits.\n"
                else:
                    model_text += "- Primary models used (no fallbacks detected)\n"

            summary = summary + model_text

        # Add SWE-bench style performance statistics
        performance = response.get("performance", {})
        if performance and "**Performance Statistics:**" not in summary:
            perf_text = "\n\n**Performance Statistics:**\n"

            duration = performance.get("review_duration_seconds", 0.0)
            tokens_used = performance.get("tokens_used", 0)
            input_tokens = performance.get("input_tokens", 0)
            output_tokens = performance.get("output_tokens", 0)
            estimated_cost = performance.get("estimated_cost_usd", 0.0)
            agents_used = performance.get("agents_used", 0)
            chunks = performance.get("chunks_received", 0)

            if duration > 0:
                perf_text += f"- **Review duration**: {duration:.1f}s\n"
            if tokens_used > 0:
                perf_text += f"- **Tokens used**: {tokens_used:,} ({input_tokens:,} input + {output_tokens:,} output)\n"
            if estimated_cost > 0:
                perf_text += f"- **Estimated cost**: ${estimated_cost:.4f} USD\n"
            if agents_used > 0:
                perf_text += f"- **Agents involved**: {agents_used}\n"
            if chunks > 0:
                perf_text += f"- **Stream chunks**: {chunks:,}\n"

            # Calculate efficiency metrics
            files_reviewed = metrics.get("files_reviewed", 0) if metrics else 0
            if duration > 0 and files_reviewed > 0:
                files_per_second = files_reviewed / duration
                perf_text += f"- **Throughput**: {files_per_second:.2f} files/second\n"

            if tokens_used > 0 and files_reviewed > 0:
                tokens_per_file = tokens_used / files_reviewed
                perf_text += f"- **Efficiency**: {tokens_per_file:.0f} tokens/file\n"

            summary = summary + perf_text

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
