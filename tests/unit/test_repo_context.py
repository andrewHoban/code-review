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

"""Unit tests for repository context tools."""

from unittest.mock import MagicMock

from app.tools.repo_context import (
    RepoContextStateKeys,
    _find_line_number,
    get_related_file,
    search_imports,
)


def test_get_related_file_found() -> None:
    """Test retrieving a related file that exists."""
    tool_context = MagicMock()
    tool_context.state = {
        RepoContextStateKeys.RELATED_FILES: [
            {
                "path": "src/utils.py",
                "content": "def helper(): pass",
                "relationship": "imported_by",
            }
        ]
    }

    result = get_related_file("src/utils.py", tool_context)

    assert result["status"] == "success"
    assert result["file"]["path"] == "src/utils.py"
    assert result["content"] == "def helper(): pass"
    assert result["relationship"] == "imported_by"


def test_get_related_file_not_found() -> None:
    """Test retrieving a related file that doesn't exist."""
    tool_context = MagicMock()
    tool_context.state = {
        RepoContextStateKeys.RELATED_FILES: [
            {"path": "src/other.py", "content": "code"}
        ]
    }

    result = get_related_file("src/utils.py", tool_context)

    assert result["status"] == "not_found"
    assert "not found in review context" in result["message"]
    assert result["file"] is None


def test_get_related_file_empty_state() -> None:
    """Test retrieving file when state is empty."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = get_related_file("src/utils.py", tool_context)

    assert result["status"] == "not_found"
    assert result["file"] is None


def test_search_imports_python() -> None:
    """Test searching for Python imports."""
    tool_context = MagicMock()
    tool_context.state = {
        RepoContextStateKeys.RELATED_FILES: [
            {
                "path": "src/main.py",
                "content": "from utils import helper\nimport os",
            }
        ],
        "changed_files": [],
    }

    result = search_imports("helper", tool_context)

    assert result["status"] == "success"
    assert result["symbol"] == "helper"
    assert result["count"] == 1
    assert result["matches"][0]["type"] == "python_import"
    assert result["matches"][0]["file"] == "src/main.py"


def test_search_imports_typescript() -> None:
    """Test searching for TypeScript imports."""
    tool_context = MagicMock()
    tool_context.state = {
        RepoContextStateKeys.RELATED_FILES: [
            {
                "path": "src/index.ts",
                "content": "import { Component } from 'react'",
            }
        ],
        "changed_files": [],
    }

    result = search_imports("Component", tool_context)

    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["matches"][0]["type"] == "typescript_import"
    assert result["matches"][0]["file"] == "src/index.ts"


def test_search_imports_multiple_matches() -> None:
    """Test searching for imports with multiple matches."""
    tool_context = MagicMock()
    tool_context.state = {
        RepoContextStateKeys.RELATED_FILES: [
            {"path": "file1.py", "content": "from utils import helper"},
            {"path": "file2.py", "content": "import helper"},
        ],
        "changed_files": [],
    }

    result = search_imports("helper", tool_context)

    assert result["status"] == "success"
    assert result["count"] == 2
    assert len(result["matches"]) == 2


def test_search_imports_no_matches() -> None:
    """Test searching for imports with no matches."""
    tool_context = MagicMock()
    tool_context.state = {
        RepoContextStateKeys.RELATED_FILES: [
            {"path": "file.py", "content": "def other(): pass"}
        ],
        "changed_files": [],
    }

    result = search_imports("nonexistent", tool_context)

    assert result["status"] == "success"
    assert result["count"] == 0
    assert len(result["matches"]) == 0


def test_search_imports_in_changed_files() -> None:
    """Test searching for imports in changed files."""
    tool_context = MagicMock()
    tool_context.state = {
        RepoContextStateKeys.RELATED_FILES: [],
        "changed_files": [
            {"path": "new_file.py", "content": "from utils import helper"}
        ],
    }

    result = search_imports("helper", tool_context)

    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["matches"][0]["file"] == "new_file.py"


def test_find_line_number() -> None:
    """Test finding line number for a symbol."""
    content = "line 1\nline 2 with symbol\nline 3"
    line_num = _find_line_number(content, "symbol")
    assert line_num == 2


def test_find_line_number_not_found() -> None:
    """Test finding line number when symbol not found."""
    content = "line 1\nline 2\nline 3"
    line_num = _find_line_number(content, "nonexistent")
    assert line_num == 0


def test_get_related_file_error_handling() -> None:
    """Test error handling in get_related_file."""
    tool_context = MagicMock()
    tool_context.state = {RepoContextStateKeys.RELATED_FILES: "invalid_type"}

    result = get_related_file("test.py", tool_context)

    assert result["status"] == "error"
    assert "message" in result
