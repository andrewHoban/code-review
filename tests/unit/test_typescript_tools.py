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

"""Unit tests for TypeScript analysis tools."""

import pytest
from unittest.mock import MagicMock

from app.tools.typescript_tools import (
    TypeScriptStateKeys,
    analyze_typescript_structure,
    check_typescript_style,
    _extract_typescript_structure,
    _calculate_typescript_style_score,
)


@pytest.mark.asyncio
async def test_analyze_typescript_structure_simple():
    """Test TypeScript structure analysis with simple code."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = """
function add(a: number, b: number): number {
    return a + b;
}

class Calculator {
    multiply(x: number, y: number): number {
        return x * y;
    }
}
"""

    result = await analyze_typescript_structure(code, tool_context)

    assert result["status"] == "success"
    assert "analysis" in result
    analysis = result["analysis"]
    assert analysis["metrics"]["function_count"] >= 1
    assert analysis["metrics"]["class_count"] >= 1


@pytest.mark.asyncio
async def test_analyze_typescript_structure_with_interfaces():
    """Test TypeScript structure analysis with interfaces."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = """
interface User {
    name: string;
    age: number;
}

export interface Config {
    apiUrl: string;
}
"""

    result = await analyze_typescript_structure(code, tool_context)

    assert result["status"] == "success"
    analysis = result["analysis"]
    assert analysis["metrics"]["interface_count"] >= 1


@pytest.mark.asyncio
async def test_analyze_typescript_structure_with_imports():
    """Test TypeScript structure analysis with imports."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = """
import { Component } from 'react';
import utils from './utils';
"""

    result = await analyze_typescript_structure(code, tool_context)

    assert result["status"] == "success"
    analysis = result["analysis"]
    assert analysis["metrics"]["import_count"] >= 1
    assert len(analysis["imports"]) >= 1


def test_extract_typescript_structure_functions():
    """Test extracting functions from TypeScript code."""
    code = """
function test1() {}
const test2 = () => {};
export function test3() {}
"""

    result = _extract_typescript_structure(code)

    assert result["metrics"]["function_count"] >= 2
    assert any(f["name"] == "test1" for f in result["functions"])


def test_extract_typescript_structure_classes():
    """Test extracting classes from TypeScript code."""
    code = """
class MyClass {}
export class AnotherClass extends BaseClass {}
"""

    result = _extract_typescript_structure(code)

    assert result["metrics"]["class_count"] >= 1
    assert any(c["name"] == "MyClass" for c in result["classes"])


def test_extract_typescript_structure_exports():
    """Test extracting exports from TypeScript code."""
    code = """
export function exportedFunc() {}
export const exportedConst = 42;
export default class DefaultClass {}
"""

    result = _extract_typescript_structure(code)

    assert result["metrics"]["export_count"] >= 1
    assert len(result["exports"]) >= 1


@pytest.mark.asyncio
async def test_check_typescript_style_pattern_based():
    """Test TypeScript style checking using pattern matching."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = "const x = 1;"

    result = await check_typescript_style(code, tool_context)

    assert result["status"] == "success"
    assert "score" in result
    assert "issues" in result
    assert 0 <= result["score"] <= 100


def test_calculate_typescript_style_score_no_issues():
    """Test style score calculation with no issues."""
    issues = []
    score = _calculate_typescript_style_score(issues)
    assert score == 100


def test_calculate_typescript_style_score_with_issues():
    """Test style score calculation with issues."""
    issues = [
        {"code": "E501", "line": 5},  # Error-level
        {"code": "W293", "line": 10},  # Warning-level
    ]
    score = _calculate_typescript_style_score(issues)
    assert score < 100
    assert score >= 0


@pytest.mark.asyncio
async def test_analyze_typescript_structure_stores_in_state():
    """Test that analysis results are stored in state."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = "function test() {}"

    await analyze_typescript_structure(code, tool_context)

    assert TypeScriptStateKeys.CODE_TO_REVIEW in tool_context.state
    assert TypeScriptStateKeys.CODE_ANALYSIS in tool_context.state
    assert TypeScriptStateKeys.CODE_LINE_COUNT in tool_context.state


@pytest.mark.asyncio
async def test_check_typescript_style_stores_in_state():
    """Test that style check results are stored in state."""
    tool_context = MagicMock()
    tool_context.state = {}

    code = "const x = 1;"

    await check_typescript_style(code, tool_context)

    assert TypeScriptStateKeys.STYLE_SCORE in tool_context.state
    assert TypeScriptStateKeys.STYLE_ISSUES in tool_context.state
    assert TypeScriptStateKeys.STYLE_ISSUE_COUNT in tool_context.state
