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
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _strip_json_fence(text: str) -> str:
    """If text is a ```json fenced block, extract the inner JSON."""
    s = text.strip()
    if not s.startswith("```"):
        return s
    # tolerate ```json or ```JSON
    first_newline = s.find("\n")
    if first_newline == -1:
        return s
    fence_header = s[:first_newline].strip().lower()
    if fence_header not in ("```json", "```"):
        return s
    # find closing fence
    closing = s.rfind("```")
    if closing <= first_newline:
        return s
    inner = s[first_newline + 1 : closing].strip()
    return inner


def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON object from text, handling multiple JSON objects and embedded text.

    Returns the last valid JSON object found, or None if none found.
    """
    if not text:
        return None

    # First try: strip JSON fence and parse
    stripped = _strip_json_fence(text)
    if stripped != text:  # Only try if we actually stripped something
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict) and (
                "summary" in parsed or "overall_status" in parsed or "metrics" in parsed
            ):
                return parsed
        except json.JSONDecodeError:
            pass

    # Second try: find all { ... } blocks and try parsing each
    # Look for JSON-like structures by matching braces
    json_candidates = []
    depth = 0
    start = -1

    for i, char in enumerate(text):
        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start != -1:
                # Found a complete JSON object
                candidate = text[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and (
                        "summary" in parsed
                        or "overall_status" in parsed
                        or "metrics" in parsed
                    ):
                        json_candidates.append(
                            (i, parsed)
                        )  # Store position and parsed dict
                except json.JSONDecodeError:
                    pass
                start = -1

    # Return the last (most recent) valid JSON object, preferring ones with more fields
    if json_candidates:
        # Sort by position (last one first) and prefer objects with more complete data
        json_candidates.sort(key=lambda x: (x[0], -len(x[1])))
        return json_candidates[-1][1]

    # Third try: try parsing the entire text as JSON (in case it's just JSON)
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, dict) and (
            "summary" in parsed or "overall_status" in parsed or "metrics" in parsed
        ):
            return parsed
    except json.JSONDecodeError:
        pass

    return None


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
        # Vertex GenAI streaming-style shape:
        # {"candidates":[{"content":{"parts":[{"text":"..."}]}}]}
        candidates = d.get("candidates")
        if isinstance(candidates, list):
            out: list[str] = []
            for cand in candidates:
                if not isinstance(cand, dict):
                    continue
                cand_content = cand.get("content")
                if isinstance(cand_content, dict):
                    parts = cand_content.get("parts")
                    if isinstance(parts, list):
                        for part in parts:
                            if isinstance(part, dict):
                                text = part.get("text")
                                if isinstance(text, str) and text:
                                    out.append(text)
            if out:
                return out

        # Common case: {"content": {"parts": [{"text": "..."}]}}
        content = d.get("content")
        if isinstance(content, dict):
            parts = content.get("parts")
            if isinstance(parts, list):
                out_parts: list[str] = []
                for part in parts:
                    if isinstance(part, dict):
                        text = part.get("text")
                        if isinstance(text, str) and text:
                            out_parts.append(text)
                if out_parts:
                    return out_parts
        # Some transports wrap multiple contents
        if isinstance(content, list):
            out = []
            for c in content:
                if isinstance(c, dict):
                    parts = c.get("parts")
                    if isinstance(parts, list):
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


def _format_model_name(model_path: str) -> str:
    """Format a model path into a human-readable name."""
    if not model_path:
        return "Unknown"

    # Extract model name from path
    # Examples:
    # "publishers/mistral-ai/models/codestral" -> "Codestral"
    # "gemini-2.5-pro" -> "Gemini 2.5 Pro"
    # "publishers/meta/models/llama-4" -> "Llama 4"

    # Handle publisher paths
    if "/models/" in model_path:
        model_name = model_path.split("/models/")[-1]
    else:
        model_name = model_path.split("/")[-1]

    # Format common model names
    model_name = model_name.replace("-", " ").replace("_", " ")
    # Capitalize words
    words = model_name.split()
    formatted = " ".join(word.capitalize() for word in words)

    # Special cases
    if "gemini" in formatted.lower():
        # Keep version numbers together: "Gemini 2.5 Pro" not "Gemini 2.5 pro"
        parts = formatted.split()
        if len(parts) >= 2 and parts[1].replace(".", "").isdigit():
            formatted = f"{parts[0]} {parts[1]} {' '.join(parts[2:])}"

    return formatted


def _get_default_model_for_agent(agent_name: str) -> str:
    """Get the default/primary model for an agent based on naming conventions."""
    # Map agent names to their default models based on config
    agent_lower = agent_name.lower()

    if "orchestrator" in agent_lower:
        return "Codestral"  # ORCHESTRATOR_MODEL
    elif "publisher" in agent_lower:
        return "Codestral"  # PUBLISHER_MODEL
    elif "analyzer" in agent_lower or "reviewer" in agent_lower:
        return "Gemini 2.5 Pro"  # CODE_ANALYZER_MODEL or FEEDBACK_SYNTHESIZER_MODEL
    elif "python" in agent_lower or "typescript" in agent_lower:
        # Language-specific agents use Gemini 2.5 Pro
        return "Gemini 2.5 Pro"
    else:
        return "Gemini 2.5 Pro"  # Default for most agents


def _estimate_token_usage(text: str, model_name: str = "") -> tuple[int, int]:
    """Estimate token usage for input and output text.

    Returns:
        Tuple of (input_tokens, output_tokens)
    """
    # Rough estimation: ~4 characters per token for English/code
    # This is a conservative estimate
    chars = len(text)
    estimated_tokens = chars // 4

    # Split between input and output (rough heuristic)
    # Most of the text is likely output from the model
    input_tokens = estimated_tokens // 3
    output_tokens = estimated_tokens - input_tokens

    return input_tokens, output_tokens


def _estimate_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """Estimate cost in USD based on token usage and model.

    Pricing (as of 2025, approximate):
    - Gemini 2.5 Pro: $1.25/$5.00 per 1M tokens (input/output)
    - Codestral: Free or very low cost
    - Llama 4: Free or very low cost
    """
    model_lower = model_name.lower()

    if "gemini" in model_lower and "2.5" in model_lower:
        # Gemini 2.5 Pro pricing
        input_cost_per_million = 1.25
        output_cost_per_million = 5.00
    elif "gemini" in model_lower:
        # Other Gemini models (use 2.5 pricing as approximation)
        input_cost_per_million = 1.25
        output_cost_per_million = 5.00
    else:
        # Free/open source models
        input_cost_per_million = 0.0
        output_cost_per_million = 0.0

    input_cost = (input_tokens / 1_000_000) * input_cost_per_million
    output_cost = (output_tokens / 1_000_000) * output_cost_per_million

    return input_cost + output_cost


def _extract_performance_metrics(
    combined_text: str, merged_state: dict[str, Any]
) -> dict[str, Any]:
    """Extract SWE-bench style performance metrics."""
    perf_metrics = merged_state.get("performance_metrics", {})

    duration = perf_metrics.get("review_duration_seconds", 0.0)
    chunks = perf_metrics.get("chunks_received", 0)

    # Estimate token usage
    input_tokens, output_tokens = _estimate_token_usage(combined_text)
    total_tokens = input_tokens + output_tokens

    # Estimate cost (use primary model if available, otherwise default to Gemini 2.5 Pro)
    model_fallbacks = merged_state.get("model_fallbacks", [])
    primary_model = "gemini-2.5-pro"  # Default
    if model_fallbacks and isinstance(model_fallbacks[0], dict):
        primary_model = model_fallbacks[0].get("primary", primary_model)

    estimated_cost = _estimate_cost(input_tokens, output_tokens, primary_model)

    # Count agents used
    agents_count = len(merged_state.get("model_fallbacks", []))
    if not agents_count:
        # Estimate based on state keys
        agents_count = len(
            [
                k
                for k in merged_state.keys()
                if "python" in k.lower()
                or "typescript" in k.lower()
                or "orchestrator" in k.lower()
                or "publisher" in k.lower()
            ]
        )
        agents_count = max(agents_count, 2)  # At least orchestrator + publisher

    return {
        "review_duration_seconds": duration,
        "tokens_used": total_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimated_cost,
        "agents_used": agents_count,
        "tool_calls": 0,  # Not easily trackable from state
        "chunks_received": chunks,
    }


def _extract_model_usage(merged_state: dict[str, Any]) -> dict[str, Any]:
    """Extract and format model usage information from state."""
    model_fallbacks = merged_state.get("model_fallbacks", [])

    # Build model usage info
    agents_info: dict[str, dict[str, str]] = {}
    fallbacks_used: list[str] = []
    agents_with_fallbacks = set()

    # Process fallback information
    for fallback_info in model_fallbacks:
        if isinstance(fallback_info, dict):
            agent_name = fallback_info.get("agent", "Unknown")
            primary = fallback_info.get("primary", "")
            fallback = fallback_info.get("fallback", "")

            agents_with_fallbacks.add(agent_name)
            agents_info[agent_name] = {
                "primary": _format_model_name(primary),
                "fallback": _format_model_name(fallback),
                "used": _format_model_name(fallback),  # Fallback was used
            }
            fallbacks_used.append(f"{agent_name} ({_format_model_name(fallback)})")

    # Try to infer other agents that were likely used (from state keys)
    # This is best-effort - we can't know for sure without tracking all agents
    potential_agents = []
    for key in merged_state.keys():
        if "python" in key.lower() or "typescript" in key.lower():
            # These suggest language-specific agents were used
            if "python" in key.lower():
                agent_name = "PythonCodeAnalyzer"  # or PythonFeedbackReviewer
            else:
                agent_name = "TypeScriptCodeAnalyzer"  # or TypeScriptFeedbackReviewer

            if agent_name not in agents_info:
                potential_agents.append(agent_name)

    # Add default models for agents we know were used but didn't have fallbacks
    for agent_name in potential_agents:
        if agent_name not in agents_with_fallbacks:
            default_model = _get_default_model_for_agent(agent_name)
            agents_info[agent_name] = {
                "primary": default_model,
                "fallback": "",
                "used": default_model,  # Primary was used
            }

    # Always include orchestrator and publisher if we have any review output
    if merged_state.get("code_review_output") or merged_state.get("formatted_output"):
        for agent_name in ["CodeReviewOrchestrator", "ReviewPublisher"]:
            if agent_name not in agents_info:
                default_model = _get_default_model_for_agent(agent_name)
                agents_info[agent_name] = {
                    "primary": default_model,
                    "fallback": "",
                    "used": default_model,
                }

    return {
        "agents": agents_info,
        "fallbacks_used": fallbacks_used,
        "used_fallback": len(fallbacks_used) > 0,
    }


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
    # Check state first (highest priority)
    structured = merged_state.get("code_review_output") or merged_state.get(
        "formatted_output"
    )
    if isinstance(structured, dict) and (
        "summary" in structured or "overall_status" in structured
    ):
        logger.info("Found structured output in state")
        if not structured.get("summary") and combined_text:
            structured["summary"] = combined_text
        # Ensure metrics are present
        if "metrics" not in structured:
            structured["metrics"] = {
                "files_reviewed": 0,
                "issues_found": 0,
                "critical_issues": 0,
                "warnings": 0,
                "suggestions": 0,
                "style_score": 0.0,
            }
        # Add model usage info
        if "model_usage" not in structured:
            structured["model_usage"] = _extract_model_usage(merged_state)
        # Add performance metrics
        if "performance" not in structured:
            structured["performance"] = _extract_performance_metrics(
                combined_text, merged_state
            )
        return structured

    if isinstance(structured, str) and structured.strip():
        # Some SDKs may store JSON string in state
        logger.info("Found string in state, attempting to parse as JSON")
        try:
            parsed = json.loads(structured)
            if isinstance(parsed, dict):
                if not parsed.get("summary") and combined_text:
                    parsed["summary"] = combined_text
                # Ensure metrics are present
                if "metrics" not in parsed:
                    parsed["metrics"] = {
                        "files_reviewed": 0,
                        "issues_found": 0,
                        "critical_issues": 0,
                        "warnings": 0,
                        "suggestions": 0,
                        "style_score": 0.0,
                    }
                # Add model usage info
                if "model_usage" not in parsed:
                    parsed["model_usage"] = _extract_model_usage(merged_state)
                # Add performance metrics
                if "performance" not in parsed:
                    parsed["performance"] = _extract_performance_metrics(
                        combined_text, merged_state
                    )
                return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse state string as JSON: {e}")
            # fall through to text handling
            combined_text = (combined_text + "\n" + structured).strip()

    if combined_text:
        # Try to extract JSON from text (handles multiple JSON objects, embedded text, etc.)
        logger.info(
            f"Attempting to extract JSON from text (length: {len(combined_text)})"
        )
        parsed = _extract_json_from_text(combined_text)
        if parsed is not None:
            logger.info("Successfully extracted JSON from text")
            # Ensure summary is populated if missing
            if not parsed.get("summary") and combined_text:
                # Try to extract a summary from the text before the JSON
                json_start = combined_text.rfind("{")
                if json_start > 0:
                    potential_summary = combined_text[:json_start].strip()
                    if potential_summary and len(potential_summary) > 20:
                        parsed["summary"] = potential_summary
                    else:
                        parsed["summary"] = combined_text
                else:
                    parsed["summary"] = combined_text
            # Ensure metrics are present
            if "metrics" not in parsed:
                parsed["metrics"] = {
                    "files_reviewed": 0,
                    "issues_found": 0,
                    "critical_issues": 0,
                    "warnings": 0,
                    "suggestions": 0,
                    "style_score": 0.0,
                }
            # Add model usage info
            if "model_usage" not in parsed:
                parsed["model_usage"] = _extract_model_usage(merged_state)
            # Add performance metrics
            if "performance" not in parsed:
                parsed["performance"] = _extract_performance_metrics(
                    combined_text, merged_state
                )
            return parsed

        logger.warning("No JSON found in text, wrapping as comment")
        # If no JSON found, wrap the text as a comment
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
            "model_usage": _extract_model_usage(merged_state),
            "performance": _extract_performance_metrics(combined_text, merged_state),
        }

    logger.error("No text or state found, returning error response")
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
        "model_usage": _extract_model_usage(merged_state),
        "performance": _extract_performance_metrics(combined_text, merged_state),
    }
