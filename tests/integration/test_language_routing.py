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

"""Integration tests for language detection and routing logic."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.models.input_schema import (
    ChangedFile,
    CodeReviewInput,
    PullRequestMetadata,
    RepositoryInfo,
    ReviewContext,
)
from app.tools.language_detection import LanguageStateKeys, detect_languages
from app.utils.input_preparation import (
    prepare_changed_files_for_detection,
    store_review_context_in_state,
)


@pytest.fixture
def python_only_pr() -> CodeReviewInput:
    """PR with only Python files."""
    return CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=1,
            repository="test/repo",
            title="Python PR",
            author="dev",
            base_branch="main",
            head_branch="feature",
        ),
        review_context=ReviewContext(
            changed_files=[
                ChangedFile(
                    path="src/main.py",
                    language="python",
                    status="modified",
                    additions=5,
                    deletions=2,
                    diff="@@ -1,3 +1,6 @@\ndef hello():\n    print('Hello')\n",
                    full_content="def hello():\n    print('Hello')\n    return True\n",
                    lines_changed=[1, 2, 3],
                )
            ],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(
                name="repo",
                primary_language="python",
                languages_used=["python"],
                total_files=10,
                has_tests=True,
            ),
        ),
    )


@pytest.fixture
def typescript_only_pr() -> CodeReviewInput:
    """PR with only TypeScript files."""
    return CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=2,
            repository="test/repo",
            title="TypeScript PR",
            author="dev",
            base_branch="main",
            head_branch="feature",
        ),
        review_context=ReviewContext(
            changed_files=[
                ChangedFile(
                    path="src/index.ts",
                    language="typescript",
                    status="modified",
                    additions=5,
                    deletions=2,
                    diff="@@ -1,3 +1,6 @@\nexport function hello() {\n  console.log('Hello');\n}\n",
                    full_content="export function hello(): void {\n  console.log('Hello');\n  return;\n}\n",
                    lines_changed=[1, 2, 3],
                )
            ],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(
                name="repo",
                primary_language="typescript",
                languages_used=["typescript"],
                total_files=15,
                has_tests=True,
            ),
        ),
    )


@pytest.fixture
def mixed_language_pr() -> CodeReviewInput:
    """PR with both Python and TypeScript files."""
    return CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=3,
            repository="test/repo",
            title="Mixed PR",
            author="dev",
            base_branch="main",
            head_branch="feature",
        ),
        review_context=ReviewContext(
            changed_files=[
                ChangedFile(
                    path="src/main.py",
                    language="python",
                    status="modified",
                    additions=3,
                    deletions=1,
                    diff="@@ -1,2 +1,4 @@\ndef test(): pass\n",
                    full_content="def test(): pass\nprint('test')\n",
                    lines_changed=[1, 2],
                ),
                ChangedFile(
                    path="src/index.ts",
                    language="typescript",
                    status="added",
                    additions=5,
                    deletions=0,
                    diff="@@ -0,0 +1,5 @@\nexport function test() {}\n",
                    full_content="export function test(): void {}\n",
                    lines_changed=[1, 2, 3, 4, 5],
                ),
            ],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(
                name="repo",
                primary_language="python",
                languages_used=["python", "typescript"],
                total_files=20,
                has_tests=True,
            ),
        ),
    )


def test_language_detection_python_only(python_only_pr: CodeReviewInput) -> None:
    """Test that Python files are detected correctly."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = prepare_changed_files_for_detection(python_only_pr)
    result = detect_languages(changed_files, tool_context)

    # Verify detection
    assert result["status"] == "success"
    assert "python" in result["languages"]
    assert "typescript" not in result["languages"]
    assert len(result["languages"]) == 1

    # Verify language files mapping
    assert "python" in result["language_files"]
    assert len(result["language_files"]["python"]) == 1
    assert result["language_files"]["python"][0]["path"] == "src/main.py"

    # Verify state storage
    assert LanguageStateKeys.DETECTED_LANGUAGES in tool_context.state
    assert LanguageStateKeys.LANGUAGE_FILES in tool_context.state
    assert "python" in tool_context.state[LanguageStateKeys.DETECTED_LANGUAGES]


def test_language_detection_typescript_only(
    typescript_only_pr: CodeReviewInput,
) -> None:
    """Test that TypeScript files are detected correctly."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = prepare_changed_files_for_detection(typescript_only_pr)
    result = detect_languages(changed_files, tool_context)

    # Verify detection
    assert result["status"] == "success"
    assert "typescript" in result["languages"]
    assert "python" not in result["languages"]
    assert len(result["languages"]) == 1

    # Verify language files mapping
    assert "typescript" in result["language_files"]
    assert len(result["language_files"]["typescript"]) == 1
    assert result["language_files"]["typescript"][0]["path"] == "src/index.ts"

    # Verify state storage
    assert "typescript" in tool_context.state[LanguageStateKeys.DETECTED_LANGUAGES]


def test_language_detection_mixed_languages(mixed_language_pr: CodeReviewInput) -> None:
    """Test that mixed language PRs are detected correctly."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = prepare_changed_files_for_detection(mixed_language_pr)
    result = detect_languages(changed_files, tool_context)

    # Verify detection
    assert result["status"] == "success"
    assert "python" in result["languages"]
    assert "typescript" in result["languages"]
    assert len(result["languages"]) == 2

    # Verify language files mapping
    assert len(result["language_files"]["python"]) == 1
    assert len(result["language_files"]["typescript"]) == 1
    assert result["language_files"]["python"][0]["path"] == "src/main.py"
    assert result["language_files"]["typescript"][0]["path"] == "src/index.ts"

    # Verify state storage
    detected = tool_context.state[LanguageStateKeys.DETECTED_LANGUAGES]
    assert "python" in detected
    assert "typescript" in detected


def test_language_detection_handles_unknown_files() -> None:
    """Test that unknown file types are handled gracefully."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = [
        {"path": "README.md", "status": "modified"},
        {"path": "config.yaml", "status": "added"},
    ]

    result = detect_languages(changed_files, tool_context)

    # Should not fail, just not detect any languages
    assert result["status"] == "success"
    assert len(result["languages"]) == 0
    assert len(result["language_files"]) == 0


def test_language_detection_handles_empty_input() -> None:
    """Test that empty file list is handled gracefully."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = detect_languages([], tool_context)

    assert result["status"] == "success"
    assert len(result["languages"]) == 0


def test_language_detection_handles_missing_path() -> None:
    """Test that files without path are handled gracefully."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = [
        {"status": "modified"},  # Missing path
        {"path": "src/test.py", "status": "added"},
    ]

    result = detect_languages(changed_files, tool_context)

    # Should still detect the valid file
    assert result["status"] == "success"
    assert "python" in result["languages"]
    assert len(result["language_files"]["python"]) == 1


def test_input_preparation_and_language_detection_integration(
    python_only_pr: CodeReviewInput,
) -> None:
    """Test full integration of input preparation and language detection."""
    # Prepare input
    changed_files = prepare_changed_files_for_detection(python_only_pr)

    # Detect languages
    tool_context = MagicMock()
    tool_context.state = {}
    result = detect_languages(changed_files, tool_context)

    # Verify end-to-end flow
    assert result["status"] == "success"
    assert "python" in result["languages"]

    # Store context in state
    state: dict[str, Any] = {}
    store_review_context_in_state(python_only_pr, state)

    # Verify state has both language detection and review context
    assert "python" in tool_context.state[LanguageStateKeys.DETECTED_LANGUAGES]
    assert "changed_files" in state
    assert len(state["changed_files"]) == 1


def test_language_detection_typescript_extensions() -> None:
    """Test that TypeScript extensions (.ts, .tsx) are detected correctly."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = [
        {"path": "src/index.ts", "status": "added"},
        {"path": "src/components/Button.tsx", "status": "added"},
    ]

    result = detect_languages(changed_files, tool_context)

    assert result["status"] == "success"
    assert "typescript" in result["languages"]
    assert len(result["language_files"]["typescript"]) == 2


def test_language_detection_python_extensions() -> None:
    """Test that Python extensions (.py, .pyi) are detected correctly."""
    tool_context = MagicMock()
    tool_context.state = {}

    changed_files = [
        {"path": "src/main.py", "status": "added"},
        {"path": "src/types.pyi", "status": "added"},
    ]

    result = detect_languages(changed_files, tool_context)

    assert result["status"] == "success"
    assert "python" in result["languages"]
    assert len(result["language_files"]["python"]) == 2
