"""Helpers to extract text and state from Agent Engine stream chunks.

Agent Engine `stream_query()` can yield different chunk types depending on SDK
version and transport:
- ADK `Event` objects (attribute access: `event.content.parts`, `event.actions.state_delta`)
- Plain `dict` objects with similar shape (key access)
- Occasionally raw strings

This module provides a schema-agnostic extractor so workflow code doesn't
silently drop output when chunk shape changes.
"""

from __future__ import annotations

import json
from typing import Any


def _as_dict(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        return obj
    return None


def _get_attr(obj: Any, name: str) -> Any:
    """Get attribute if present, else None."""
    try:
        return getattr(obj, name)
    except Exception:
        return None


def extract_text_parts(chunk: Any) -> list[str]:
    """Extract text parts from a single streamed chunk."""
    if chunk is None:
        return []

    if isinstance(chunk, str):
        return [chunk] if chunk else []

    # Dict-shaped chunk
    if (d := _as_dict(chunk)) is not None:
        # Common case: {"content": {"parts": [{"text": "..."}]}}
        content = d.get("content")
        if isinstance(content, dict):
            parts = content.get("parts")
            if isinstance(parts, list):
                out: list[str] = []
                for part in parts:
                    if isinstance(part, dict):
                        text = part.get("text")
                        if isinstance(text, str) and text:
                            out.append(text)
                if out:
                    return out

        # Alternate: {"text": "..."}
        text = d.get("text")
        if isinstance(text, str) and text:
            return [text]

        # Sometimes content itself is a string
        if isinstance(content, str) and content:
            return [content]

        return []

    # ADK Event-ish object
    content = _get_attr(chunk, "content")
    if content is not None:
        parts = _get_attr(content, "parts")
        if parts:
            out = []
            for part in parts:
                text = _get_attr(part, "text")
                if isinstance(text, str) and text:
                    out.append(text)
            if out:
                return out

    text = _get_attr(chunk, "text")
    if isinstance(text, str) and text:
        return [text]

    return []


def extract_state_delta(chunk: Any) -> dict[str, Any]:
    """Extract state delta from a single streamed chunk (best-effort)."""
    if chunk is None:
        return {}

    # Dict-shaped chunk
    if (d := _as_dict(chunk)) is not None:
        actions = d.get("actions")
        if isinstance(actions, dict):
            state_delta = actions.get("state_delta")
            if isinstance(state_delta, dict):
                return state_delta
        return {}

    # ADK Event-ish object
    actions = _get_attr(chunk, "actions")
    if actions is None:
        return {}

    state_delta = _get_attr(actions, "state_delta")
    if isinstance(state_delta, dict):
        return state_delta

    return {}


def extract_text_and_state(
    chunks: list[Any],
) -> tuple[str, dict[str, Any]]:
    """Extract concatenated text and merged state_delta from a chunk list."""
    all_text_parts: list[str] = []
    merged_state: dict[str, Any] = {}

    for chunk in chunks:
        all_text_parts.extend(extract_text_parts(chunk))
        merged_state.update(extract_state_delta(chunk))

    combined_text = "\n".join([t for t in all_text_parts if t]).strip()
    return combined_text, merged_state


def coerce_review_output(
    combined_text: str, merged_state: dict[str, Any]
) -> dict[str, Any]:
    """Return a CodeReviewOutput-ish dict from extracted text/state.

    Priority:
    1) `code_review_output` in state
    2) `formatted_output` in state
    3) JSON object in `combined_text`
    4) Wrap plain text as a COMMENT
    """
    structured = merged_state.get("code_review_output") or merged_state.get(
        "formatted_output"
    )
    if isinstance(structured, dict) and (
        "summary" in structured or "overall_status" in structured
    ):
        if not structured.get("summary") and combined_text:
            structured["summary"] = combined_text
        return structured

    if isinstance(structured, str) and structured.strip():
        # Some SDKs may store JSON string in state
        try:
            parsed = json.loads(structured)
            if isinstance(parsed, dict):
                if not parsed.get("summary") and combined_text:
                    parsed["summary"] = combined_text
                return parsed
        except json.JSONDecodeError:
            # fall through to text handling
            combined_text = (combined_text + "\n" + structured).strip()

    if combined_text:
        # If publisher outputs JSON-only, this should succeed.
        try:
            parsed = json.loads(combined_text)
            if isinstance(parsed, dict) and (
                "summary" in parsed or "overall_status" in parsed
            ):
                return parsed
        except json.JSONDecodeError:
            pass

        return {
            "summary": combined_text,
            "inline_comments": [],
            "overall_status": "COMMENT",
            "metrics": {
                "files_reviewed": 0,
                "issues_found": 0,
                "critical_issues": 0,
                "warnings": 0,
                "suggestions": 0,
                "style_score": 0.0,
            },
        }

    return {
        "summary": (
            "Code review completed successfully, but the review content could not be "
            "extracted from the agent response. This usually indicates a streaming "
            "response schema mismatch. Please check workflow logs for details."
        ),
        "inline_comments": [],
        "overall_status": "COMMENT",
        "metrics": {
            "files_reviewed": 0,
            "issues_found": 0,
            "critical_issues": 0,
            "warnings": 0,
            "suggestions": 0,
            "style_score": 0.0,
        },
    }
