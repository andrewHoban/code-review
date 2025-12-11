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

"""TypeScript-specific analysis tools for code review."""

import asyncio
import logging
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from app.config import TYPESCRIPT_MAX_LINE_LENGTH

logger = logging.getLogger(__name__)


# State keys for TypeScript analysis
class TypeScriptStateKeys:
    """Constants for TypeScript-specific state keys."""

    CODE_TO_REVIEW = "typescript_code_to_review"
    CODE_ANALYSIS = "typescript_code_analysis"
    CODE_LINE_COUNT = "typescript_code_line_count"
    STYLE_SCORE = "typescript_style_score"
    STYLE_ISSUES = "typescript_style_issues"
    STYLE_ISSUE_COUNT = "typescript_style_issue_count"


async def analyze_typescript_structure(
    code: str, tool_context: ToolContext
) -> dict[str, Any]:
    """
    Analyzes TypeScript code structure using pattern matching and regex.

    Note: Full TypeScript AST parsing would require TypeScript compiler API.
    This is a simplified version using regex patterns.

    Args:
        code: TypeScript source code to analyze
        tool_context: ADK tool context

    Returns:
        Dictionary containing structural analysis
    """
    logger.info("Tool: Analyzing TypeScript code structure...")

    try:
        if not code:
            code = tool_context.state.get(TypeScriptStateKeys.CODE_TO_REVIEW, "")
            if not code:
                return {
                    "status": "error",
                    "message": "No TypeScript code provided or found in state",
                }

        # Parse in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            analysis = await loop.run_in_executor(
                executor, _extract_typescript_structure, code
            )

        # Store code and analysis for other agents to access
        tool_context.state[TypeScriptStateKeys.CODE_TO_REVIEW] = code
        tool_context.state[TypeScriptStateKeys.CODE_ANALYSIS] = analysis
        tool_context.state[TypeScriptStateKeys.CODE_LINE_COUNT] = len(code.splitlines())

        logger.info(
            f"Tool: Analysis complete - {analysis['metrics']['function_count']} "
            f"functions, {analysis['metrics']['class_count']} classes"
        )

        return {
            "status": "success",
            "analysis": analysis,
            "summary": f"Found {analysis['metrics']['function_count']} functions, "
            f"{analysis['metrics']['class_count']} classes, "
            f"{analysis['metrics']['import_count']} imports",
        }

    except Exception as e:
        error_msg = f"TypeScript analysis failed: {e!s}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "message": error_msg,
        }


def _extract_typescript_structure(code: str) -> dict[str, Any]:
    """
    Extract structural information from TypeScript code using regex patterns.
    This is a simplified parser - full AST parsing would require TypeScript compiler.
    """
    functions = []
    classes = []
    interfaces = []
    imports = []
    exports = []

    lines = code.split("\n")

    # Pattern for function declarations
    function_pattern = re.compile(
        r"(?:export\s+)?(?:async\s+)?(?:function\s+)?(\w+)\s*[=:]?\s*(?:async\s+)?\([^)]*\)\s*[:=]?\s*(?:Promise<.*?>)?\s*\{",
        re.MULTILINE,
    )

    # Pattern for class declarations
    class_pattern = re.compile(
        r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w\s,]+)?\s*\{",
        re.MULTILINE,
    )

    # Pattern for interface declarations
    interface_pattern = re.compile(
        r"(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+[\w\s,]+)?\s*\{",
        re.MULTILINE,
    )

    # Pattern for imports
    import_pattern = re.compile(
        r"import\s+(?:(?:\{[^}]+\}|\*\s+as\s+\w+|\w+)\s+from\s+)?['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )

    # Pattern for exports
    export_pattern = re.compile(
        r"export\s+(?:default\s+)?(?:class|function|interface|const|let|var|type|enum)\s+(\w+)",
        re.MULTILINE,
    )

    # Find functions
    for match in function_pattern.finditer(code):
        func_name = match.group(1)
        line_num = code[: match.start()].count("\n") + 1
        functions.append(
            {
                "name": func_name,
                "lineno": line_num,
                "is_async": "async" in match.group(0),
            }
        )

    # Find classes
    for match in class_pattern.finditer(code):
        class_name = match.group(1)
        line_num = code[: match.start()].count("\n") + 1
        classes.append({"name": class_name, "lineno": line_num})

    # Find interfaces
    for match in interface_pattern.finditer(code):
        interface_name = match.group(1)
        line_num = code[: match.start()].count("\n") + 1
        interfaces.append({"name": interface_name, "lineno": line_num})

    # Find imports
    for match in import_pattern.finditer(code):
        module = match.group(1)
        imports.append({"module": module, "type": "import"})

    # Find exports
    for match in export_pattern.finditer(code):
        export_name = match.group(1)
        exports.append({"name": export_name})

    return {
        "functions": functions,
        "classes": classes,
        "interfaces": interfaces,
        "imports": imports,
        "exports": exports,
        "metrics": {
            "line_count": len(lines),
            "function_count": len(functions),
            "class_count": len(classes),
            "interface_count": len(interfaces),
            "import_count": len(imports),
            "export_count": len(exports),
        },
    }


async def check_typescript_style(
    code: str, tool_context: ToolContext
) -> dict[str, Any]:
    """
    Checks TypeScript code style using ESLint (if available) or pattern matching.

    Args:
        code: TypeScript source code to check
        tool_context: ADK tool context

    Returns:
        Dictionary containing style score and issues
    """
    logger.info("Tool: Checking TypeScript code style...")

    try:
        # Retrieve code from state if not provided
        if not code:
            code = tool_context.state.get(TypeScriptStateKeys.CODE_TO_REVIEW, "")
            if not code:
                return {
                    "status": "error",
                    "message": "No TypeScript code provided or found in state",
                }

        # Try ESLint first, fall back to pattern matching
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            try:
                result = await loop.run_in_executor(
                    executor, _perform_typescript_style_check_eslint, code
                )
            except FileNotFoundError:
                # ESLint not available, use pattern-based checking
                logger.warning("ESLint not found, using pattern-based style checking")
                result = await loop.run_in_executor(
                    executor, _perform_typescript_style_check_patterns, code
                )

        # Store results in state
        tool_context.state[TypeScriptStateKeys.STYLE_SCORE] = result["score"]
        tool_context.state[TypeScriptStateKeys.STYLE_ISSUES] = result["issues"]
        tool_context.state[TypeScriptStateKeys.STYLE_ISSUE_COUNT] = result[
            "issue_count"
        ]

        logger.info(
            f"Tool: Style check complete - Score: {result['score']}/100, "
            f"Issues: {result['issue_count']}"
        )

        return result

    except Exception as e:
        error_msg = f"TypeScript style check failed: {e!s}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        tool_context.state[TypeScriptStateKeys.STYLE_SCORE] = 0
        tool_context.state[TypeScriptStateKeys.STYLE_ISSUES] = []

        return {
            "status": "error",
            "message": error_msg,
            "score": 0,
        }


def _perform_typescript_style_check_eslint(code: str) -> dict[str, Any]:
    """Perform style check using ESLint if available."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
        # Set restrictive permissions (read/write for owner only)
        os.chmod(tmp_path, 0o600)

    try:
        # Try to run ESLint
        result = subprocess.run(
            ["npx", "eslint", "--format", "json", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # No issues
            return {
                "status": "success",
                "score": 100,
                "issue_count": 0,
                "issues": [],
                "summary": "Style score: 100/100 with 0 violations",
            }

        # Parse ESLint JSON output
        import json

        try:
            eslint_output = json.loads(result.stdout)
            issues = []
            for file_result in eslint_output:
                for message in file_result.get("messages", []):
                    issues.append(
                        {
                            "line": message.get("line", 0),
                            "column": message.get("column", 0),
                            "code": message.get("ruleId", "unknown"),
                            "message": message.get("message", ""),
                        }
                    )

            score = _calculate_typescript_style_score(issues)

            return {
                "status": "success",
                "score": score,
                "issue_count": len(issues),
                "issues": issues[:10],
                "summary": f"Style score: {score}/100 with {len(issues)} violations",
            }
        except json.JSONDecodeError:
            # Fall back to pattern checking
            return _perform_typescript_style_check_patterns(code)

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # ESLint not available or timed out
        return _perform_typescript_style_check_patterns(code)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _perform_typescript_style_check_patterns(code: str) -> dict[str, Any]:
    """Perform basic style checking using pattern matching."""
    issues = []
    lines = code.split("\n")

    # Check for common style issues
    for i, line in enumerate(lines, 1):
        # Trailing whitespace
        if line.rstrip() != line:
            issues.append(
                {
                    "line": i,
                    "column": len(line.rstrip()),
                    "code": "W293",
                    "message": "trailing whitespace",
                }
            )

        # Line too long
        if len(line) > TYPESCRIPT_MAX_LINE_LENGTH:
            issues.append(
                {
                    "line": i,
                    "column": TYPESCRIPT_MAX_LINE_LENGTH,
                    "code": "E501",
                    "message": f"line too long (over {TYPESCRIPT_MAX_LINE_LENGTH} characters)",
                }
            )

        # Missing semicolon (basic check)
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith("//")
            and not stripped.startswith("*")
            and not stripped.startswith("}")
            and not stripped.startswith("{")
            and not stripped.endswith(";")
            and not stripped.endswith("{")
            and not stripped.endswith("}")
            and "function" not in stripped
            and "if" not in stripped
            and "for" not in stripped
            and "while" not in stripped
            and "return" not in stripped
        ):
            # This is a very basic check - may have false positives
            pass

    score = _calculate_typescript_style_score(issues)

    return {
        "status": "success",
        "score": score,
        "issue_count": len(issues),
        "issues": issues[:10],
        "summary": f"Style score: {score}/100 with {len(issues)} violations (pattern-based)",
    }


def _calculate_typescript_style_score(issues: list[dict[str, Any]]) -> int:
    """Calculate weighted style score based on violation severity."""
    if not issues:
        return 100

    # Define weights by error type
    weights = {
        "E": 5,  # Error-level issues
        "W": 2,  # Warning-level issues
    }

    total_deduction = 0
    for issue in issues:
        code = issue.get("code", "E000")
        code_prefix = code[0] if code else "E"
        weight = weights.get(code_prefix, 3)
        total_deduction += weight

    # Cap at 100 points deduction
    return max(0, 100 - min(total_deduction, 100))


# Export tools
analyze_typescript_structure_tool = FunctionTool(func=analyze_typescript_structure)
check_typescript_style_tool = FunctionTool(func=check_typescript_style)
