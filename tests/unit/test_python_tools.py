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

"""Unit tests for Python analysis tools."""

import ast
from typing import Any

import pytest

from app.tools.python_tools import (
    _calculate_avg_function_length,
    _calculate_python_style_score,
    _extract_python_structure,
)


def test_extract_python_structure_simple_function() -> None:
    """Test AST analysis of a simple Python function."""
    code = """
def add(a, b):
    return a + b
"""
    tree = ast.parse(code)
    result = _extract_python_structure(tree, code)

    assert result["functions"] == [
        {
            "name": "add",
            "args": ["a", "b"],
            "lineno": 2,
            "has_docstring": False,
            "is_async": False,
            "decorators": [],
        }
    ]
    assert result["metrics"]["function_count"] == 1
    assert result["metrics"]["class_count"] == 0


def test_extract_python_structure_with_class() -> None:
    """Test AST analysis with a class."""
    code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
    tree = ast.parse(code)
    result = _extract_python_structure(tree, code)

    assert len(result["classes"]) == 1
    assert result["classes"][0]["name"] == "Calculator"
    assert result["classes"][0]["methods"] == ["add"]
    assert result["metrics"]["class_count"] == 1


def test_calculate_avg_function_length() -> None:
    """Test average function length calculation."""
    code = """
def short():
    pass

def long():
    x = 1
    y = 2
    z = 3
    return x + y + z
"""
    tree = ast.parse(code)
    avg_length = _calculate_avg_function_length(tree)

    # short() is 2 lines (def + pass), long() is 5 lines (def + 4 statements)
    # Average = (2 + 5) / 2 = 3.5
    expected_avg = 3.5
    assert avg_length == pytest.approx(expected_avg, abs=0.5)


def test_calculate_python_style_score_no_issues() -> None:
    """Test style score calculation with no issues."""
    issues: list[dict[str, Any]] = []
    score = _calculate_python_style_score(issues)
    assert score == 100


def test_calculate_python_style_score_with_issues() -> None:
    """Test style score calculation with issues."""
    issues = [
        {"code": "E302", "line": 5},  # Blank line error (weight 5)
        {"code": "W293", "line": 10},  # Trailing whitespace (weight 2)
    ]
    score = _calculate_python_style_score(issues)
    assert score < 100
    assert score >= 0


def test_extract_python_structure_imports() -> None:
    """Test import extraction."""
    code = """
import os
from typing import List, Dict
"""
    tree = ast.parse(code)
    result = _extract_python_structure(tree, code)

    assert result["metrics"]["import_count"] == 2
    assert any(imp["module"] == "os" for imp in result["imports"])
    assert any(imp["module"] == "typing" for imp in result["imports"])
