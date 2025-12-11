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

"""Configuration for code review agent models and settings."""

import os

# Model configuration
# Language detection needs intelligence to handle edge cases
LANGUAGE_DETECTOR_MODEL = os.getenv("LANGUAGE_DETECTOR_MODEL", "gemini-3-pro-preview")

# Code analysis requires complex reasoning - use 3.0 model
CODE_ANALYZER_MODEL = os.getenv("CODE_ANALYZER_MODEL", "gemini-3-pro-preview")

# Style checking is deterministic - use faster model
STYLE_CHECKER_MODEL = os.getenv("STYLE_CHECKER_MODEL", "gemini-2.5-flash")

# Test analysis requires complex reasoning
TEST_ANALYZER_MODEL = os.getenv("TEST_ANALYZER_MODEL", "gemini-3-pro-preview")

# Feedback synthesis needs good reasoning but not cutting edge
FEEDBACK_SYNTHESIZER_MODEL = os.getenv("FEEDBACK_SYNTHESIZER_MODEL", "gemini-2.5-pro")

# Review configuration
MAX_INLINE_COMMENTS = int(os.getenv("MAX_INLINE_COMMENTS", "50"))
REVIEW_TIMEOUT_SECONDS = int(os.getenv("REVIEW_TIMEOUT_SECONDS", "300"))

# Style checking configuration
PYTHON_STYLE_IGNORE = os.getenv("PYTHON_STYLE_IGNORE", "E501,W503").split(
    ","
)  # Line length, line break before binary operator
TYPESCRIPT_STYLE_CONFIG = os.getenv("TYPESCRIPT_STYLE_CONFIG", ".eslintrc.json")

# Style score weights for Python code review
PYTHON_STYLE_WEIGHTS = {
    "E1": 10,  # Indentation errors
    "E2": 3,  # Whitespace errors
    "E3": 5,  # Blank line errors
    "E4": 8,  # Import errors
    "E5": 5,  # Line length
    "E7": 7,  # Statement errors
    "E9": 10,  # Syntax errors
    "W2": 2,  # Whitespace warnings
    "W3": 2,  # Blank line warnings
    "W5": 3,  # Line break warnings
    "N8": 7,  # Naming conventions
}

# Maximum line length for style checking
PYTHON_MAX_LINE_LENGTH = int(os.getenv("PYTHON_MAX_LINE_LENGTH", "100"))
TYPESCRIPT_MAX_LINE_LENGTH = int(os.getenv("TYPESCRIPT_MAX_LINE_LENGTH", "120"))
