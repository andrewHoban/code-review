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

"""Unit tests for error handling in code review utilities."""

import pytest

from app.utils.input_preparation import parse_review_input


def test_parse_review_input_empty_string() -> None:
    """Test parsing empty input string."""
    with pytest.raises(ValueError, match="No JSON object found"):
        parse_review_input("")


def test_parse_review_input_invalid_json() -> None:
    """Test parsing invalid JSON."""
    invalid_json = "{ invalid json }"

    with pytest.raises(ValueError, match="Invalid JSON format"):
        parse_review_input(invalid_json)


def test_parse_review_input_malformed_json() -> None:
    """Test parsing malformed JSON."""
    malformed = '{"pr_metadata": {invalid}'

    with pytest.raises(ValueError):
        parse_review_input(malformed)


def test_parse_review_input_no_json_object() -> None:
    """Test parsing text with no JSON object."""
    text_only = "This is just plain text with no JSON"

    with pytest.raises(ValueError, match="No JSON object found"):
        parse_review_input(text_only)


def test_parse_review_input_incomplete_json() -> None:
    """Test parsing incomplete JSON (missing closing brace)."""
    incomplete = '{"pr_metadata": {"pr_number": 1}'

    with pytest.raises(ValueError):
        parse_review_input(incomplete)
