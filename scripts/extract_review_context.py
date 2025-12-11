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

# Maximum file size to include (100KB)
MAX_FILE_SIZE = 100 * 1024

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


def get_file_content(repo: Repo, file_path: str, commit_sha: str | None = None) -> str:
    """Get file content from repository."""
    try:
        if commit_sha:
            commit = repo.commit(commit_sha)
            blob = commit.tree / file_path
        else:
            blob = repo.head.commit.tree / file_path
        return blob.data_stream.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def get_diff(repo: Repo, base_sha: str, head_sha: str, file_path: str) -> str:
    """Get unified diff for a file."""
    try:
        diff = repo.git.diff(base_sha, head_sha, "--", file_path)
        return diff
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
    repo: Repo, changed_files: list[str], head_sha: str | None = None
) -> dict[str, list[str]]:
    """Find files related to changed files (imports, dependencies)."""
    related = {}
    for file_path in changed_files:
        language = detect_language(file_path)
        if not language:
            continue

        try:
            content = get_file_content(repo, file_path, head_sha)
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
                            if (repo.head.commit.tree / potential_path).exists():
                                imports.append(potential_path)

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
                            if (repo.head.commit.tree / potential_path).exists():
                                imports.append(potential_path)

            related[file_path] = imports
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
    """Extract review context from PR and build agent input."""
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
    for file_path, status_char in changed_paths:
        # Skip binary and large files
        try:
            file_size = os.path.getsize(os.path.join(repo_path, file_path))
            if file_size > MAX_FILE_SIZE:
                print(f"Skipping large file: {file_path} ({file_size} bytes)")
                continue
        except Exception:
            pass

        language = detect_language(file_path)
        if not language or language not in ["python", "typescript"]:
            continue

        # Get file content and diff
        full_content = get_file_content(repo, file_path, head_sha)
        diff = get_diff(repo, base_sha, head_sha, file_path)
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

    if not processed_files:
        raise ValueError("No supported files found in PR")

    # Find related files
    changed_paths_list = [f.path for f in processed_files]
    related_map = find_related_files(repo, changed_paths_list, head_sha)
    related_files_list = []
    for file_path, related_paths in related_map.items():
        for related_path in related_paths[
            :5
        ]:  # Limit to 5 related files per changed file
            try:
                content = get_file_content(repo, related_path, head_sha)
                lang = detect_language(related_path)
                related_files_list.append(
                    RelatedFile(
                        path=related_path,
                        content=content,
                        relationship=f"imported by {file_path}",
                        language=lang or "unknown",
                    )
                )
            except Exception:
                pass

    # Find test files
    test_map = find_test_files(repo, changed_paths_list, head_sha)
    test_files_list = []
    for file_path, test_paths in test_map.items():
        for test_path in test_paths:
            try:
                content = get_file_content(repo, test_path, head_sha)
                lang = detect_language(test_path)
                test_files_list.append(
                    TestFile(
                        path=test_path,
                        content=content,
                        tests_for=file_path,
                        language=lang or "unknown",
                    )
                )
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

        print(
            f"Successfully extracted review context: {len(input_data.review_context.changed_files)} files"
        )
        print(f"Output written to: {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
