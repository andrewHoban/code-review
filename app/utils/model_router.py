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

"""Reusable model router that automatically falls back to secondary model on failure."""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import Agent
from google.adk.events import Event
from pydantic import PrivateAttr

from app.config import FALLBACK_ENABLED
from app.utils.model_fallback import get_fallback_model, is_token_quota_error

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    A reusable router that tries a primary model and falls back to a secondary model
    when the primary fails due to token/quota limits.
    """

    def __init__(
        self,
        primary_model: str,
        secondary_model: str | None = None,
    ) -> None:
        """
        Initialize the model router.

        Args:
            primary_model: Primary model to use (e.g., "gemini-2.5-pro")
            secondary_model: Secondary fallback model (auto-selected if None)
        """
        self.primary_model = primary_model
        self.secondary_model = secondary_model or get_fallback_model(primary_model)
        self.last_used_model: str | None = None
        self.used_fallback = False

    def get_model(self) -> str:
        """
        Get the current model to use.

        Returns:
            Model path/name to use
        """
        # If we've already fallen back, continue using secondary
        if self.used_fallback:
            return self.secondary_model

        # Try primary first
        return self.primary_model

    def should_fallback(self, error: Exception) -> bool:
        """
        Check if we should fall back to secondary model based on error.

        Args:
            error: The exception that occurred

        Returns:
            True if we should fall back
        """
        return FALLBACK_ENABLED and is_token_quota_error(error)

    def record_fallback(self) -> None:
        """Record that we've fallen back to secondary model."""
        if not self.used_fallback:
            self.used_fallback = True
            self.last_used_model = self.secondary_model
            logger.warning(
                f"Falling back from {self.primary_model} to {self.secondary_model} "
                "due to token/quota limits"
            )

    def get_usage_info(self) -> dict[str, Any]:
        """
        Get information about which model was used.

        Returns:
            Dictionary with model usage information
        """
        model_used = self.secondary_model if self.used_fallback else self.primary_model
        return {
            "model": model_used,
            "primary_model": self.primary_model,
            "secondary_model": self.secondary_model,
            "used_fallback": self.used_fallback,
        }


class RoutedAgent(Agent):
    """
    An Agent that uses a ModelRouter to automatically fall back to secondary model
    when primary model hits token/quota limits.
    """

    _router: ModelRouter = PrivateAttr()

    def __init__(
        self,
        name: str,
        primary_model: str,
        secondary_model: str | None = None,
        **agent_kwargs: Any,
    ) -> None:
        """
        Initialize a routed agent.

        Args:
            name: Agent name
            primary_model: Primary model to use
            secondary_model: Secondary fallback model (auto-selected if None)
            **agent_kwargs: Additional arguments passed to Agent
        """
        router = ModelRouter(primary_model, secondary_model)
        # Initialize with primary model, then attach router as a private attribute.
        # (Setting it before `super().__init__` can be wiped by Pydantic model init.)
        super().__init__(name=name, model=router.get_model(), **agent_kwargs)
        object.__setattr__(self, "_router", router)

    async def _run_async_impl(self, ctx: Any) -> AsyncGenerator[Event, None]:
        """Run the agent with automatic fallback on token/quota errors.

        Note: ADK's `Agent._run_async_impl` signature is `(self, ctx) -> AsyncGenerator[Event, None]`.
        Older/internal variants may pass additional args; we intentionally match the current
        public signature used by `Runner`.
        """

        router = self._router

        def _record_fallback_in_state() -> None:
            session = getattr(ctx, "session", None)
            state = getattr(session, "state", None) if session is not None else None
            if not isinstance(state, dict):
                return
            model_fallbacks = state.setdefault("model_fallbacks", [])
            if not isinstance(model_fallbacks, list):
                return
            model_fallbacks.append(
                {
                    "agent": self.name,
                    "primary": router.primary_model,
                    "fallback": router.secondary_model,
                }
            )

        async def _run_stream() -> AsyncGenerator[Event, None]:
            self.model = router.get_model()
            logger.debug(f"Agent {self.name} using model: {self.model}")
            async for event in super()._run_async_impl(ctx):
                yield event

        # Try primary model first
        try:
            async for event in _run_stream():
                yield event
            if router.used_fallback:
                _record_fallback_in_state()
            return
        except Exception as e:
            if not router.should_fallback(e):
                logger.error(f"Agent {self.name} failed with non-quota error: {e}")
                raise

            router.record_fallback()

            # Switch to secondary model and retry
            try:
                logger.info(
                    f"Agent {self.name} retrying with fallback model: {router.get_model()}"
                )
                async for event in _run_stream():
                    yield event
                _record_fallback_in_state()
                return
            except Exception as fallback_error:
                logger.error(
                    f"Agent {self.name} failed with both primary ({router.primary_model}) "
                    f"and secondary ({router.secondary_model}) models. "
                    f"Original error: {e}. Fallback error: {fallback_error}"
                )
                raise RuntimeError(
                    f"Agent {self.name} failed with both models. "
                    f"Primary ({router.primary_model}) error: {e}. "
                    f"Secondary ({router.secondary_model}) error: {fallback_error}"
                ) from fallback_error


def create_routed_agent(
    name: str,
    primary_model: str,
    secondary_model: str | None = None,
    **agent_kwargs: Any,
) -> RoutedAgent:
    """
    Create an agent with automatic model fallback.

    Args:
        name: Agent name
        primary_model: Primary model (e.g., "gemini-2.5-pro")
        secondary_model: Secondary fallback model (auto-selected if None)
        **agent_kwargs: Additional agent arguments

    Returns:
        RoutedAgent instance

    Example:
        ```python
        agent = create_routed_agent(
            name="CodeAnalyzer",
            primary_model="gemini-2.5-pro",
            secondary_model="publishers/google/models/llama-4",  # Optional
            instruction="Analyze code...",
            tools=[my_tool],
        )
        ```
    """
    return RoutedAgent(
        name=name,
        primary_model=primary_model,
        secondary_model=secondary_model,
        **agent_kwargs,
    )
