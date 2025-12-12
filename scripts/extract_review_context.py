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

"""Extract review context from a GitHub PR and build the agent input payload."""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from git import Repo
from github import Auth, Github

from app.models.input_schema import (
    ChangedFile,
    CodeReviewInput,
    FileDependencies,
    PullRequestMetadata,
    RelatedFile,
    RepositoryInfo,
    ReviewContext,
    TestFile,
)
from app.utils.security import (
    MAX_FILE_CONTENT_SIZE,
    sanitize_file_path,
    validate_commit_sha,
    validate_content_size,
)

# Maximum file size to include (100KB)
MAX_FILE_SIZE = MAX_FILE_CONTENT_SIZE

# Maximum reverse dependencies (files that import changed files) per changed file
MAX_REVERSE_DEPENDENCIES = int(os.getenv("MAX_REVERSE_DEPENDENCIES", "10"))

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


def get_file_content(
    repo: Repo,
    file_path: str,
    commit_sha: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """Get file content from repository with security validation."""
    try:
        # Validate and sanitize file path
        if repo_root:
            sanitized_path = sanitize_file_path(file_path, repo_root)
            file_path = str(sanitized_path.relative_to(repo_root))

        # Validate commit SHA if provided
        if commit_sha:
            validate_commit_sha(commit_sha)
            commit = repo.commit(commit_sha)
            blob = commit.tree / file_path
        else:
            blob = repo.head.commit.tree / file_path

        content = blob.data_stream.read().decode("utf-8", errors="ignore")
        # Validate content size
        validate_content_size(content, MAX_FILE_CONTENT_SIZE)
        return content
    except (ValueError, OSError) as e:
        print(f"Warning: Could not read file {file_path}: {e}")
        return ""
    except Exception:
        return ""


def get_diff(
    repo: Repo,
    base_sha: str,
    head_sha: str,
    file_path: str,
    repo_root: Path | None = None,
) -> str:
    """Get unified diff for a file with security validation."""
    try:
        # Validate commit SHAs
        validate_commit_sha(base_sha)
        validate_commit_sha(head_sha)

        # Validate and sanitize file path
        if repo_root:
            sanitized_path = sanitize_file_path(file_path, repo_root)
            file_path = str(sanitized_path.relative_to(repo_root))

        diff = repo.git.diff(base_sha, head_sha, "--", file_path)
        # Validate diff size
        validate_content_size(diff, MAX_FILE_CONTENT_SIZE)
        return diff
    except (ValueError, OSError) as e:
        print(f"Warning: Could not get diff for {file_path}: {e}")
        return ""
    except Exception:
        return ""


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


def find_related_files(
    repo: Repo,
    changed_files: list[str],
    head_sha: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, list[str]]:
    """Find files related to changed files (imports, dependencies) with security validation."""
    related = {}

    for file_path in changed_files:
        language = detect_language(file_path)
        if not language:
            continue

        try:
            # Validate file path
            if repo_root:
                sanitize_file_path(file_path, repo_root)

            content = get_file_content(repo, file_path, head_sha, repo_root)
            imports = []

            if language == "python":
                # Find Python imports
                import_pattern = r"^(?:from\s+([\w.]+)|import\s+([\w.]+))"
                for line in content.split("\n"):
                    match = re.match(import_pattern, line.strip())
                    if match:
                        module = match.group(1) or match.group(2)
                        # Try to find corresponding file
                        module_path = module.replace(".", "/")
                        for ext in [".py", ".pyi"]:
                            potential_path = f"{module_path}{ext}"
                            # Validate potential path
                            try:
                                if repo_root:
                                    sanitize_file_path(potential_path, repo_root)
                                if (repo.head.commit.tree / potential_path).exists():
                                    imports.append(potential_path)
                            except ValueError:
                                continue  # Skip invalid paths

            elif language in ["typescript", "javascript"]:
                # Find TypeScript/JavaScript imports
                import_pattern = r"import\s+.*from\s+['\"]([^'\"]+)['\"]"
                for line in content.split("\n"):
                    match = re.search(import_pattern, line)
                    if match:
                        import_path = match.group(1)
                        # Resolve relative imports
                        if import_path.startswith("."):
                            base_dir = str(Path(file_path).parent)
                            resolved = Path(base_dir) / import_path
                            potential_path = str(
                                resolved.with_suffix(
                                    ".ts" if language == "typescript" else ".js"
                                )
                            )
                            # Validate resolved path
                            try:
                                if repo_root:
                                    sanitize_file_path(potential_path, repo_root)
                                if (repo.head.commit.tree / potential_path).exists():
                                    imports.append(potential_path)
                            except ValueError:
                                continue  # Skip invalid paths

            related[file_path] = imports[:10]  # Limit imports per file
        except (ValueError, OSError) as e:
            print(f"Warning: Error processing {file_path}: {e}")
            related[file_path] = []
        except Exception:
            related[file_path] = []

    return related


def find_test_files(
    repo: Repo, changed_files: list[str], head_sha: str | None = None
) -> dict[str, list[str]]:
    """Find test files for changed files."""
    test_files = {}
    repo_root = Path(repo.working_dir)

    for file_path in changed_files:
        language = detect_language(file_path)
        if not language:
            continue

        file_stem = Path(file_path).stem
        file_dir = Path(file_path).parent
        potential_tests = []

        # Look for test files in same directory and test directories
        for test_dir in [
            file_dir,
            repo_root / "tests",
            repo_root / "test",
            file_dir / "tests",
            file_dir / "test",
        ]:
            if not test_dir.exists():
                continue

            for test_file in test_dir.rglob("*"):
                if not test_file.is_file():
                    continue

                # Ensure test_file is absolute and under repo_root
                try:
                    test_file_abs = test_file.resolve()
                    repo_root_abs = repo_root.resolve()
                    test_path = str(test_file_abs.relative_to(repo_root_abs))
                except ValueError:
                    # Skip files not under repo_root
                    continue

                test_lang = detect_language(test_path)
                if test_lang == language and is_test_file(test_path, test_lang):
                    # Check if test file name suggests it tests this file
                    test_stem = test_file.stem
                    if (
                        file_stem in test_stem
                        or test_stem.replace("test_", "").replace("_test", "")
                        == file_stem
                    ):
                        potential_tests.append(test_path)

        test_files[file_path] = potential_tests[
            :3
        ]  # Limit to 3 test files per changed file

    return test_files


def get_repository_info(repo: Repo) -> RepositoryInfo:
    """Get repository information."""
    languages = set()
    total_files = 0
    has_tests = False

    for item in repo.head.commit.tree.traverse():
        if item.type == "blob":
            total_files += 1
            lang = detect_language(item.path)
            if lang:
                languages.add(lang)
            if is_test_file(item.path, lang):
                has_tests = True

    primary_language = (
        "python"
        if "python" in languages
        else (next(iter(languages)) if languages else "unknown")
    )

    return RepositoryInfo(
        name=os.path.basename(repo.working_dir),
        primary_language=primary_language,
        languages_used=list(languages),
        total_files=total_files,
        has_tests=has_tests,
    )


def extract_review_context(
    repo_path: str,
    pr_number: int,
    repository: str,
    base_sha: str,
    head_sha: str,
    github_token: str | None = None,
) -> CodeReviewInput:
    """Extract review context from PR and build agent input with security validation."""
    # Validate and sanitize repository path
    repo_root = Path(repo_path).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise ValueError(f"Invalid repository path: {repo_path}")

    # Validate commit SHAs
    validate_commit_sha(base_sha)
    validate_commit_sha(head_sha)

    repo = Repo(repo_path)

    # Get PR metadata from GitHub API
    pr_metadata = None
    if github_token:
        try:
            auth = Auth.Token(github_token)
            g = Github(auth=auth)
            repo_obj = g.get_repo(repository)
            pr = repo_obj.get_pull(pr_number)
            pr_metadata = PullRequestMetadata(
                pr_number=pr.number,
                repository=repository,
                title=pr.title,
                description=pr.body or "",
                author=pr.user.login,
                base_branch=pr.base.ref,
                head_branch=pr.head.ref,
                base_sha=pr.base.sha,
                head_sha=pr.head.sha,
            )
        except Exception as e:
            print(f"Warning: Could not fetch PR metadata from GitHub: {e}")
            print("Using provided metadata instead.")

    if not pr_metadata:
        pr_metadata = PullRequestMetadata(
            pr_number=pr_number,
            repository=repository,
            title="",
            description="",
            author="",
            base_branch="",
            head_branch="",
            base_sha=base_sha,
            head_sha=head_sha,
        )

    # Get changed files
    try:
        diff_output = repo.git.diff("--name-status", base_sha, head_sha)
        changed_paths = []
        for line in diff_output.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status = parts[0]
                file_path = parts[1]
                if status.startswith("R"):
                    # Renamed file - get both old and new paths
                    old_path, new_path = file_path.split("\t")
                    changed_paths.append((new_path, status))
                else:
                    changed_paths.append((file_path, status))
    except Exception as e:
        print(f"Error getting changed files: {e}")
        changed_paths = []

    # Process changed files
    processed_files = []
    skipped_files = []  # Track skipped files for better error messages
    for file_path, status_char in changed_paths:
        # Validate and sanitize file path
        try:
            sanitize_file_path(file_path, repo_root)
        except ValueError as e:
            print(f"Skipping invalid file path {file_path}: {e}")
            skipped_files.append((file_path, "invalid path"))
            continue

        # Skip binary and large files
        try:
            file_size = os.path.getsize(os.path.join(repo_path, file_path))
            if file_size > MAX_FILE_SIZE:
                print(f"Skipping large file: {file_path} ({file_size} bytes)")
                skipped_files.append((file_path, f"too large ({file_size} bytes)"))
                continue
        except Exception:
            pass

        language = detect_language(file_path)
        if not language or language not in ["python", "typescript"]:
            skipped_files.append(
                (file_path, f"unsupported language ({language or 'unknown'})")
            )
            continue

        # Get diff with security validation
        diff = get_diff(repo, base_sha, head_sha, file_path, repo_root)
        lines_changed = get_changed_lines(diff)

        # Count additions and deletions
        additions = diff.count("\n+") - diff.count("\n+++")
        deletions = diff.count("\n-") - diff.count("\n---")

        # Determine status
        if status_char.startswith("A"):
            status = "added"
        elif status_char.startswith("D"):
            status = "deleted"
        elif status_char.startswith("R"):
            status = "renamed"
        else:
            status = "modified"

        # OPTIMIZATION: Only include full_content for new files or major refactors
        # For modified files where < 50% changed, diff is sufficient
        # This reduces token usage by 30-40% for typical PRs
        full_content = ""
        total_lines = len(
            get_file_content(repo, file_path, head_sha, repo_root).split("\n")
        )

        if status == "added":
            # New files: include full content (reviewers need context)
            full_content = get_file_content(repo, file_path, head_sha, repo_root)
        elif total_lines > 0 and (additions + deletions) > (total_lines * 0.5):
            # Major refactor (>50% of file changed): include full content
            full_content = get_file_content(repo, file_path, head_sha, repo_root)
        # else: Modified files with <50% changes - diff is sufficient, leave full_content=""

        changed_file = ChangedFile(
            path=file_path,
            language=language,
            status=status,
            additions=additions,
            deletions=deletions,
            diff=diff,
            full_content=full_content,
            lines_changed=lines_changed,
        )
        processed_files.append(changed_file)

    # Handle case where no supported files are found
    if not processed_files:
        print("Info: No supported files (Python/TypeScript) found in PR.")
        if skipped_files:
            print(f"Found {len(skipped_files)} changed file(s) that were skipped:")
            for file_path, reason in skipped_files[:10]:  # Show up to 10 skipped files
                print(f"  - {file_path}: {reason}")
            if len(skipped_files) > 10:
                print(f"  ... and {len(skipped_files) - 10} more")
        else:
            print("No changed files detected in this PR.")
        print(
            "This PR may contain only non-code files, documentation, or unsupported languages."
        )
        # Continue to create a valid payload with empty lists
        # The workflow can check if changed_files is empty to skip the review step

    # OPTIMIZATION: Related files loaded on-demand via get_related_file_tool
    # Only store paths, not content - agents can load when needed
    # This reduces initial payload by 10-15% for typical PRs
    changed_paths_list = [f.path for f in processed_files]
    related_map = find_related_files(repo, changed_paths_list, head_sha, repo_root)
    related_files_list = []

    # Store related file paths with metadata (but not content)
    # Agents can use get_related_file_tool to load content on-demand
    for file_path, related_paths in related_map.items():
        for related_path in related_paths[:5]:  # Limit to 5 per changed file
            try:
                sanitize_file_path(related_path, repo_root)
                lang = detect_language(related_path)
                # Store path and relationship, but load content on-demand
                # This reduces token usage - content only loaded if agent needs it
                related_files_list.append(
                    RelatedFile(
                        path=related_path,
                        content="",  # Empty - loaded on-demand via tool
                        relationship=f"imported by {file_path}",
                        language=lang or "unknown",
                    )
                )
            except (ValueError, OSError) as e:
                print(f"Warning: Skipping related file {related_path}: {e}")
                continue
            except Exception:
                pass

    # Find test files
    test_map = find_test_files(repo, changed_paths_list, head_sha)
    test_files_list = []
    for file_path, test_paths in test_map.items():
        for test_path in test_paths:
            try:
                # Validate test file path
                sanitize_file_path(test_path, repo_root)
                content = get_file_content(repo, test_path, head_sha, repo_root)
                lang = detect_language(test_path)
                test_files_list.append(
                    TestFile(
                        path=test_path,
                        content=content,
                        tests_for=file_path,
                        language=lang or "unknown",
                    )
                )
            except (ValueError, OSError) as e:
                print(f"Warning: Skipping test file {test_path}: {e}")
                continue
            except Exception:
                pass

    # Build dependency map
    dependency_map = {}
    for file_path, related_paths in related_map.items():
        dependency_map[file_path] = FileDependencies(
            imports=related_paths[:10],  # Limit imports
            imported_by=[],  # Would need reverse lookup
        )

    # Get repository info
    repo_info = get_repository_info(repo)

    # Build review context
    review_context = ReviewContext(
        changed_files=processed_files,
        related_files=related_files_list,
        test_files=test_files_list,
        dependency_map=dependency_map,
        repository_info=repo_info,
    )

    return CodeReviewInput(pr_metadata=pr_metadata, review_context=review_context)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract review context from PR")
    parser.add_argument("--repo-path", required=True, help="Path to repository")
    parser.add_argument("--pr-number", type=int, required=True, help="PR number")
    parser.add_argument(
        "--repository", required=True, help="Repository name (owner/repo)"
    )
    parser.add_argument("--base-sha", required=True, help="Base commit SHA")
    parser.add_argument("--head-sha", required=True, help="Head commit SHA")
    parser.add_argument("--github-token", help="GitHub token for API access")
    parser.add_argument("--output", required=True, help="Output JSON file path")

    args = parser.parse_args()

    try:
        input_data = extract_review_context(
            repo_path=args.repo_path,
            pr_number=args.pr_number,
            repository=args.repository,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            github_token=args.github_token,
        )

        # Write output
        with open(args.output, "w") as f:
            json.dump(input_data.model_dump(), f, indent=2)

        num_files = len(input_data.review_context.changed_files)
        if num_files == 0:
            print("No supported files found in PR. Review will be skipped.")
            print(f"Output written to: {args.output}")
            # Exit with code 2 to indicate "no work to do" (not an error)
            # This allows workflows to skip the review step gracefully
            sys.exit(2)
        else:
            print(f"Successfully extracted review context: {num_files} files")
            print(f"Output written to: {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
