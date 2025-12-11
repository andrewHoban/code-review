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

"""Repository context tools for accessing related files and dependencies."""

import logging
import re
from typing import Any

from google.adk.tools import FunctionTool, ToolContext

from app.utils.security import (
    MAX_SYMBOL_LENGTH,
    sanitize_symbol_for_regex,
)

logger = logging.getLogger(__name__)


# State keys for repository context
class RepoContextStateKeys:
    """Constants for repository context state keys."""

    RELATED_FILES = "related_files"
    TEST_FILES = "test_files"
    DEPENDENCY_MAP = "dependency_map"


def get_related_file(file_path: str, tool_context: ToolContext) -> dict[str, Any]:
    """
    Retrieves a related file from the review context.

    Args:
        file_path: Path of the file to retrieve
        tool_context: ADK tool context

    Returns:
        Dictionary with file content and metadata
    """
    logger.info(f"Tool: Retrieving related file: {file_path}")

    try:
        related_files = tool_context.state.get(RepoContextStateKeys.RELATED_FILES, [])

        # Validate that related_files is a list
        if not isinstance(related_files, list):
            raise TypeError(
                f"Expected list for related_files, got {type(related_files).__name__}"
            )

        # Search for exact match
        for file in related_files:
            if isinstance(file, dict) and file.get("path") == file_path:
                return {
                    "status": "success",
                    "file": file,
                    "content": file.get("content", ""),
                    "relationship": file.get("relationship", ""),
                }

        # Not found
        return {
            "status": "not_found",
            "message": f"File {file_path} not found in review context",
            "file": None,
        }

    except Exception as e:
        error_msg = f"Failed to retrieve related file: {e!s}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "message": error_msg,
            "file": None,
        }


def search_imports(symbol: str, tool_context: ToolContext) -> dict[str, Any]:
    """
    Searches for import statements of a symbol across review context.

    Args:
        symbol: Symbol name to search for (function, class, variable)
        tool_context: ADK tool context

    Returns:
        Dictionary with search results
    """
    logger.info(f"Tool: Searching for imports of symbol: {symbol}")

    try:
        # Validate and sanitize symbol to prevent ReDoS
        if len(symbol) > MAX_SYMBOL_LENGTH:
            raise ValueError(f"Symbol too long (max {MAX_SYMBOL_LENGTH} characters)")
        escaped_symbol = sanitize_symbol_for_regex(symbol)

        related_files = tool_context.state.get(RepoContextStateKeys.RELATED_FILES, [])
        changed_files = tool_context.state.get("changed_files", [])

        all_files = related_files + changed_files
        matches = []

        # Search for import patterns with sanitized symbol
        # Python: from module import symbol, import module
        # TypeScript: import { symbol } from 'module', import symbol from 'module'
        python_pattern = re.compile(
            rf"(?:from\s+[\w.]+|import)\s+.*\b{escaped_symbol}\b", re.IGNORECASE
        )
        typescript_pattern = re.compile(
            rf"import\s+(?:\{{\s*{escaped_symbol}\s*\}}|{escaped_symbol})\s+from",
            re.IGNORECASE,
        )

        for file_info in all_files:
            if isinstance(file_info, dict):
                content = file_info.get("content", "")
                path = file_info.get("path", "")

                # Determine file type from extension
                is_python = path.endswith((".py", ".pyi"))
                is_typescript = path.endswith((".ts", ".tsx", ".js", ".jsx"))

                # Check Python imports (only for Python files)
                if is_python and python_pattern.search(content):
                    matches.append(
                        {
                            "file": path,
                            "type": "python_import",
                            "line": _find_line_number(content, symbol),
                        }
                    )

                # Check TypeScript imports (only for TypeScript/JavaScript files)
                if is_typescript and typescript_pattern.search(content):
                    matches.append(
                        {
                            "file": path,
                            "type": "typescript_import",
                            "line": _find_line_number(content, symbol),
                        }
                    )

        return {
            "status": "success",
            "symbol": symbol,
            "matches": matches,
            "count": len(matches),
        }

    except Exception as e:
        error_msg = f"Import search failed: {e!s}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "message": error_msg,
            "matches": [],
        }


def _find_line_number(content: str, symbol: str) -> int:
    """Find line number where symbol appears."""
    for i, line in enumerate(content.split("\n"), 1):
        if symbol in line:
            return i
    return 0


# Export tools
get_related_file_tool = FunctionTool(func=get_related_file)
search_imports_tool = FunctionTool(func=search_imports)
