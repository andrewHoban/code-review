# ruff: noqa
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

import logging
import os
from typing import AsyncGenerator

import google.auth
from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps.app import App
from google.adk.events import Event

from app.config import LANGUAGE_DETECTOR_MODEL, LANGUAGE_DETECTOR_FALLBACK_MODEL
from app.models.output_schema import CodeReviewOutput
from app.prompts.static_context import STATIC_REVIEW_CONTEXT

logger = logging.getLogger(__name__)


_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


def create_code_review_agent(model_name: str) -> Agent:
    """Create a code review agent with the specified model.

    Uses structured output via Pydantic model to guarantee valid JSON.

    Args:
        model_name: The model to use (e.g., "gemini-2.5-pro", "gemini-2.5-flash")

    Returns:
        Configured Agent instance for code review
    """
    return Agent(
        name="CodeReviewer",
        model=model_name,
        description="Expert code reviewer for GitHub PRs using comprehensive review principles",
        instruction=f"""{STATIC_REVIEW_CONTEXT}

You are an expert code reviewer analyzing GitHub pull requests.

INPUT FORMAT:
You'll receive JSON with:
- pr_metadata: PR title, description, author
- review_context.changed_files: Files with diffs, full_content, language
- review_context.related_files: Context from related files
- review_context.test_files: Test coverage

YOUR TASK:
1. Read all changed files and their full content
2. Apply the review principles above to the code
3. Check for: Correctness, Security, Performance, Design, Test quality
4. Return a structured JSON response with your findings

OUTPUT STRUCTURE:
- summary: Overall review summary in markdown (use "LGTM - no significant issues." if clean)
- overall_status: One of ["APPROVED", "NEEDS_CHANGES", "COMMENT"]
  - APPROVED: No issues or only minor suggestions
  - NEEDS_CHANGES: Has HIGH severity issues
  - COMMENT: Has MEDIUM severity issues worth noting
- inline_comments: Array of specific line comments (empty if no issues)
  - path: File path
  - line: Line number
  - severity: One of ["error", "warning", "info", "suggestion"]
  - body: Comment in markdown with issue + fix suggestion
- metrics: Review statistics
  - files_reviewed: Number of files reviewed
  - issues_found: Total issues count
  - critical_issues: HIGH severity count
  - warnings: MEDIUM severity count
  - suggestions: LOW severity count

CRITICAL REMINDERS:
- 60-80% of PRs should mostly pass - be constructive, not harsh
- Be specific with file:line references in inline_comments
- Use "APPROVED" liberally when code is clean
- No praise, no "what went well" sections, no congratulations
- Focus exclusively on issues that need addressing
""",
        output_key="code_review_output",
        output_schema=CodeReviewOutput,  # ADK will automatically configure Gemini's response_schema
        generate_content_config={
            "temperature": 0.3,
            "max_output_tokens": 8192,
        },
    )


def _is_model_error(exception: Exception) -> bool:
    """Check if an exception is model-related and should trigger fallback.

    Args:
        exception: The exception to check

    Returns:
        True if the exception indicates a model-related error that should trigger fallback
    """
    error_type = type(exception).__name__
    error_message = str(exception).lower()

    # Check exception type
    model_error_types = [
        "ResourceExhausted",
        "InvalidArgument",
        "NotFound",
        "FailedPrecondition",
        "Unavailable",
        "PermissionDenied",  # Sometimes model access issues
    ]

    if error_type in model_error_types:
        return True

    # Check error message for model-related keywords
    model_error_keywords = [
        "model",
        "quota",
        "rate limit",
        "unavailable",
        "not found",
        "not available",
        "resource exhausted",
        "permission denied",
    ]

    if any(keyword in error_message for keyword in model_error_keywords):
        return True

    # Check exception chain for nested model errors
    exc: Exception | None = exception
    for _ in range(5):  # Limit recursion depth
        if exc is None:
            break
        if type(exc).__name__ in model_error_types:
            return True
        cause = getattr(exc, "__cause__", None)
        context = getattr(exc, "__context__", None)
        exc = cause if cause is not None else context

    return False


class ModelFallbackAgent(BaseAgent):
    """Agent wrapper that falls back to a secondary model if the primary fails.

    Tries the primary agent first. If it encounters a model-related error,
    automatically retries with the fallback agent. Tracks which model was
    used in session state.
    """

    def __init__(self, primary_agent: Agent, fallback_agent: Agent):
        """Initialize the fallback agent wrapper.

        Args:
            primary_agent: The primary agent to try first
            fallback_agent: The fallback agent to use if primary fails
        """
        super().__init__(name="CodeReviewerWithFallback")
        # Use object.__setattr__ to bypass Pydantic's field validation
        object.__setattr__(self, "primary_agent", primary_agent)
        object.__setattr__(self, "fallback_agent", fallback_agent)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Run the agent with automatic fallback on model errors.

        Tries primary agent first. On model-related errors, falls back to
        secondary agent. Tracks which model succeeded in ctx.session.state.
        """
        # Try primary agent first
        try:
            ctx.session.state["model_used"] = LANGUAGE_DETECTOR_MODEL
            logger.info(f"Using primary model: {LANGUAGE_DETECTOR_MODEL}")

            async for event in self.primary_agent.run_async(ctx):
                yield event

            # Primary succeeded - we're done
            logger.info(f"Primary model {LANGUAGE_DETECTOR_MODEL} succeeded")
            return

        except Exception as e:
            # Check if this is a model-related error
            if not _is_model_error(e):
                # Not a model error - re-raise it
                logger.error(
                    f"Primary model {LANGUAGE_DETECTOR_MODEL} failed with "
                    f"non-model error: {type(e).__name__}: {e}"
                )
                raise

            # Model-related error - try fallback
            logger.warning(
                f"Primary model {LANGUAGE_DETECTOR_MODEL} failed with model error: "
                f"{type(e).__name__}: {e}. Falling back to {LANGUAGE_DETECTOR_FALLBACK_MODEL}"
            )

            # Update state to indicate we're using fallback
            ctx.session.state["model_used"] = LANGUAGE_DETECTOR_FALLBACK_MODEL

            # Try fallback agent with the same context
            async for event in self.fallback_agent.run_async(ctx):
                yield event

            logger.info(f"Fallback model {LANGUAGE_DETECTOR_FALLBACK_MODEL} succeeded")


# Create primary and fallback agents
_primary_agent = create_code_review_agent(LANGUAGE_DETECTOR_MODEL)
_fallback_agent = create_code_review_agent(LANGUAGE_DETECTOR_FALLBACK_MODEL)

# Wrap in fallback agent - this becomes the root_agent
root_agent = ModelFallbackAgent(
    primary_agent=_primary_agent,
    fallback_agent=_fallback_agent,
)


app = App(root_agent=root_agent, name="app")
