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

"""Unit tests for language detection."""

import pytest
from unittest.mock import MagicMock

from app.tools.language_detection import detect_languages


def test_detect_languages_python():
    """Test detection of Python files."""
    changed_files = [
        {"path": "src/main.py", "status": "modified"},
        {"path": "src/utils.py", "status": "added"},
    ]

    tool_context = MagicMock()
    tool_context.state = {}

    result = detect_languages(changed_files, tool_context)

    assert result["status"] == "success"
    assert "python" in result["languages"]
    assert len(result["language_files"]["python"]) == 2


def test_detect_languages_typescript():
    """Test detection of TypeScript files."""
    changed_files = [
        {"path": "src/index.ts", "status": "modified"},
        {"path": "src/components/Button.tsx", "status": "added"},
    ]

    tool_context = MagicMock()
    tool_context.state = {}

    result = detect_languages(changed_files, tool_context)

    assert result["status"] == "success"
    assert "typescript" in result["languages"]
    assert len(result["language_files"]["typescript"]) == 2


def test_detect_languages_mixed():
    """Test detection of mixed language files."""
    changed_files = [
        {"path": "src/main.py", "status": "modified"},
        {"path": "src/index.ts", "status": "modified"},
    ]

    tool_context = MagicMock()
    tool_context.state = {}

    result = detect_languages(changed_files, tool_context)

    assert result["status"] == "success"
    assert "python" in result["languages"]
    assert "typescript" in result["languages"]
    assert len(result["languages"]) == 2


def test_detect_languages_unknown():
    """Test handling of unknown file types."""
    changed_files = [
        {"path": "README.md", "status": "modified"},
    ]

    tool_context = MagicMock()
    tool_context.state = {}

    result = detect_languages(changed_files, tool_context)

    # Should not fail, just not detect any languages
    assert result["status"] == "success"
    assert len(result["languages"]) == 0
