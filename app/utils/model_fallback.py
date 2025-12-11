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

"""Model fallback utility for handling token/quota limits with open source fallbacks."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def is_token_quota_error(error: Exception) -> bool:
    """
    Check if an error indicates token/quota exhaustion.

    Args:
        error: The exception to check

    Returns:
        True if the error indicates token/quota issues
    """
    error_str = str(error).upper()
    error_type = type(error).__name__.upper()

    # Check for common token/quota error indicators
    token_quota_indicators = [
        "RESOURCE_EXHAUSTED",
        "429",
        "QUOTA_EXCEEDED",
        "RATE_LIMIT",
        "TOKEN_LIMIT",
        "CONTEXT_LENGTH",
        "MAX_TOKENS",
        "OUT_OF_TOKENS",
        "QUOTA",
    ]

    return any(
        indicator in error_str or indicator in error_type
        for indicator in token_quota_indicators
    )


def get_fallback_model(primary_model: str) -> str:
    """
    Get the fallback open source model for a given primary Gemini model.

    Args:
        primary_model: The primary Gemini model name (e.g., "gemini-2.5-pro")

    Returns:
        The fallback open source model path
    """
    # Map models to their fallbacks (all must be available in Vertex AI)
    # Strategy: Gemini 2.5 Pro → Llama 4 (free, good quality)
    #          Codestral → Llama 4 (if Codestral fails)
    fallback_map = {
        # Gemini 2.5 Pro: Fallback to Llama 4 (free, good quality)
        "gemini-2.5-pro": "publishers/google/models/llama-4",
        # Gemini Flash models: Fallback to Codestral (code-focused, free)
        "gemini-2.5-flash": "publishers/mistral-ai/models/codestral",
        "gemini-2.0-flash": "publishers/mistral-ai/models/codestral",
        # Codestral: Fallback to Llama 4 (if Codestral fails)
        "publishers/mistral-ai/models/codestral": "publishers/google/models/llama-4",
        "codestral": "publishers/google/models/llama-4",
        # Default fallback for any model
        "default": "publishers/google/models/llama-4",
    }

    # Check for exact match first
    if primary_model in fallback_map:
        return fallback_map[primary_model]

    # Check if it's Codestral
    if "codestral" in primary_model.lower():
        return fallback_map.get(
            "publishers/mistral-ai/models/codestral", fallback_map["default"]
        )

    # Check if it's a Gemini model (starts with "gemini")
    if primary_model.startswith("gemini"):
        # Use Llama 4 for pro models, Codestral for flash models
        if "flash" in primary_model.lower():
            return fallback_map["gemini-2.5-flash"]
        else:
            # Gemini 2.5 Pro falls back to Llama 4
            return fallback_map["gemini-2.5-pro"]

    # Default fallback
    logger.warning(f"Unknown model {primary_model}, using default fallback")
    return fallback_map["default"]


def get_model_display_name(model_path: str) -> str:
    """
    Get a human-readable display name for a model.

    Args:
        model_path: The model path (e.g., "publishers/google/models/llama-4")

    Returns:
        Human-readable model name
    """
    # Extract model name from path
    if "/" in model_path:
        model_name = model_path.split("/")[-1]
    else:
        model_name = model_path

    # Map to display names
    display_names = {
        "llama-4": "Llama 4",
        "llama-3-70b": "Llama 3 70B",
        "llama-3-8b": "Llama 3 8B",
        "llama-3.3-70b": "Llama 3.3 70B",
        "codestral": "Codestral",
        "mistral-large": "Mistral Large",
        "mistral-medium": "Mistral Medium",
        "mistral-small": "Mistral Small",
        "devstral-2": "Devstral2",
        "devstral2": "Devstral2",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "gemini-3-pro": "Gemini 3.0 Pro",
        "gemini-3-pro-preview": "Gemini 3.0 Pro",
    }

    # Check for exact match
    if model_name in display_names:
        return display_names[model_name]

    # Check for partial match
    for key, display in display_names.items():
        if key in model_name.lower():
            return display

    # Return formatted version
    return model_name.replace("-", " ").title()


class ModelUsageTracker:
    """Tracks which models were used during a review session."""

    def __init__(self) -> None:
        """Initialize the model usage tracker."""
        self.usage: dict[str, dict[str, Any]] = {}
        self.fallbacks_used: list[str] = []

    def record_model_usage(
        self, agent_name: str, model: str, used_fallback: bool = False
    ) -> None:
        """
        Record that a model was used by an agent.

        Args:
            agent_name: Name of the agent using the model
            model: The model path/name used
            used_fallback: Whether this was a fallback model
        """
        display_name = get_model_display_name(model)
        self.usage[agent_name] = {
            "model": model,
            "display_name": display_name,
            "used_fallback": used_fallback,
        }

        if used_fallback:
            self.fallbacks_used.append(f"{agent_name} ({display_name})")

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of model usage.

        Returns:
            Dictionary with usage summary
        """
        return {
            "agents": self.usage,
            "fallbacks_used": self.fallbacks_used,
            "used_fallback": len(self.fallbacks_used) > 0,
        }

    def get_fallback_message(self) -> str:
        """
        Get a message explaining fallback usage for inclusion in review output.

        Returns:
            Markdown-formatted message about fallback usage
        """
        if not self.fallbacks_used:
            return ""

        agents = ", ".join(self.fallbacks_used)
        return (
            f"\n\n---\n"
            f"**Note:** This review used open source fallback models ({agents}) "
            f"due to Gemini token/quota limits. Review quality may be slightly reduced."
        )
