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

"""Language detection tools for code review."""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from google.adk.tools import FunctionTool, ToolContext

logger = logging.getLogger(__name__)

# State keys for language detection
class LanguageStateKeys:
    """Constants for language detection state keys."""

    DETECTED_LANGUAGES = "detected_languages"
    LANGUAGE_FILES = "language_files_map"


def detect_languages(
    changed_files: List[Dict[str, Any]], tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Analyzes file extensions and content to determine programming languages.

    Args:
        changed_files: List of changed file dictionaries with 'path' key
        tool_context: ADK tool context

    Returns:
        Dictionary mapping languages to lists of file paths
    """
    logger.info("Tool: Detecting languages in changed files...")

    try:
        languages = defaultdict(list)

        # Language detection by file extension
        language_extensions = {
            "python": [".py", ".pyi", ".pyx"],
            "typescript": [".ts", ".tsx"],
            "javascript": [".js", ".jsx"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
            "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
            "c": [".c", ".h"],
        }

        for file_info in changed_files:
            file_path = file_info.get("path", "")
            if not file_path:
                continue

            path_obj = Path(file_path)
            ext = path_obj.suffix.lower()

            # Detect language from extension
            detected = False
            for lang, exts in language_extensions.items():
                if ext in exts:
                    languages[lang].append(file_info)
                    detected = True
                    break

            if not detected:
                # Unknown language - log but don't fail
                logger.warning(f"Unknown file type: {file_path}")

        # Store in state
        result_dict = {lang: files for lang, files in languages.items()}
        tool_context.state[LanguageStateKeys.DETECTED_LANGUAGES] = result_dict
        tool_context.state[LanguageStateKeys.LANGUAGE_FILES] = result_dict

        logger.info(
            f"Tool: Detected languages: {list(result_dict.keys())} "
            f"with {sum(len(files) for files in result_dict.values())} files"
        )

        return {
            "status": "success",
            "languages": list(result_dict.keys()),
            "language_files": result_dict,
            "summary": f"Detected {len(result_dict)} language(s): {', '.join(result_dict.keys())}",
        }

    except Exception as e:
        error_msg = f"Language detection failed: {str(e)}"
        logger.error(f"Tool: {error_msg}", exc_info=True)

        return {
            "status": "error",
            "message": error_msg,
            "languages": [],
            "language_files": {},
        }


# Export tool
detect_languages_tool = FunctionTool(func=detect_languages)
