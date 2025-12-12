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

# mypy: disable-error-code="attr-defined,arg-type"
import logging
import os
from typing import Any

from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines.templates.adk import AdkApp

from app.agent import root_agent
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        setup_telemetry()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)

        # Set location if provided
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

        # Call parent set_up to initialize session service and runner
        # This is required for the agent engine to handle sessions properly
        super().set_up()

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough approximation: 1 token ≈ 4 characters)."""
        if not text:
            return 0
        # Rough estimate: 1 token ≈ 4 characters for English/code
        # This is approximate - actual tokenization varies
        return len(text.encode("utf-8")) // 4

    def _log_token_usage(self, input_text: str, output_text: str | None = None) -> None:
        """Log estimated token usage for monitoring and optimization."""
        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(output_text) if output_text else 0
        total_tokens = input_tokens + output_tokens

        # Log token usage
        self.logger.log_struct(
            {
                "event": "token_usage_estimate",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
            severity="INFO",
        )

        # Warn if token usage is high (threshold: 500K tokens)
        if total_tokens > 500000:
            self.logger.warning(
                f"High token usage detected: {total_tokens:,} tokens "
                f"(input: {input_tokens:,}, output: {output_tokens:,}). "
                "Consider optimizing: reduce full_content, enable caching, consolidate agents."
            )

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = [*operations.get("", []), "register_feedback"]
        return operations


agent_engine = AgentEngineApp(
    agent=root_agent,
    artifact_service_builder=lambda: GcsArtifactService(bucket_name=logs_bucket_name)
    if logs_bucket_name
    else InMemoryArtifactService(),
)
