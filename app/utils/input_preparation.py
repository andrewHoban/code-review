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

"""Utilities for preparing and parsing code review input."""

import json
import logging
from typing import Any

from app.models.input_schema import CodeReviewInput
from app.utils.security import MAX_JSON_PAYLOAD_SIZE, validate_content_size

logger = logging.getLogger(__name__)


def parse_review_input(user_message: str) -> CodeReviewInput:
    """
    Parse user message containing JSON payload into CodeReviewInput model.

    Args:
        user_message: JSON string or text containing JSON

    Returns:
        CodeReviewInput model instance

    Raises:
        ValueError: If JSON cannot be parsed or validated
    """
    try:
        # Validate input size to prevent DoS
        validate_content_size(user_message, MAX_JSON_PAYLOAD_SIZE)

        # Try to extract JSON from message (might be wrapped in markdown or text)
        # Look for JSON object
        json_start = user_message.find("{")
        json_end = user_message.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = user_message[json_start:json_end]

            # Validate extracted JSON size
            validate_content_size(json_str, MAX_JSON_PAYLOAD_SIZE)

            # Parse with size limit protection
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                raise ValueError(f"Invalid JSON format: {e}") from e

            # Validate JSON structure depth to prevent stack overflow
            _validate_json_depth(data, max_depth=20)

            return CodeReviewInput.model_validate(data)
        else:
            raise ValueError("No JSON object found in message")

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Failed to parse review input: {e}")
        raise ValueError(f"Failed to parse review input: {e}") from e


def _validate_json_depth(obj: Any, max_depth: int = 20, current_depth: int = 0) -> None:
    """
    Validate JSON structure depth to prevent stack overflow attacks.

    Args:
        obj: JSON object to validate
        max_depth: Maximum allowed nesting depth
        current_depth: Current nesting depth

    Raises:
        ValueError: If JSON structure is too deeply nested
    """
    if current_depth > max_depth:
        raise ValueError(f"JSON structure too deeply nested (max {max_depth} levels)")

    if isinstance(obj, dict):
        for value in obj.values():
            _validate_json_depth(value, max_depth, current_depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            _validate_json_depth(item, max_depth, current_depth + 1)


def prepare_changed_files_for_detection(
    review_input: CodeReviewInput,
) -> list[dict[str, Any]]:
    """
    Extract changed files in format needed for language detection tool.

    Args:
        review_input: Parsed CodeReviewInput

    Returns:
        List of file dictionaries with 'path' key
    """
    return [
        {"path": file.path, "status": file.status, "language": file.language}
        for file in review_input.review_context.changed_files
    ]


def store_review_context_in_state(
    review_input: CodeReviewInput, state: dict[str, Any]
) -> None:
    """
    Store review context in session state for agents to access.

    Args:
        review_input: Parsed CodeReviewInput
        state: Session state dictionary
    """
    # Store full context
    state["review_context"] = review_input.review_context.model_dump()
    state["pr_metadata"] = review_input.pr_metadata.model_dump()

    # Store changed files for easy access
    state["changed_files"] = [
        file.model_dump() for file in review_input.review_context.changed_files
    ]

    # Store related files
    state["related_files"] = [
        file.model_dump() for file in review_input.review_context.related_files
    ]

    # Store test files
    state["test_files"] = [
        file.model_dump() for file in review_input.review_context.test_files
    ]

    # Store dependency map
    state["dependency_map"] = review_input.review_context.dependency_map

    logger.info(
        f"Stored review context: {len(review_input.review_context.changed_files)} "
        f"changed files, {len(review_input.review_context.related_files)} related files"
    )
