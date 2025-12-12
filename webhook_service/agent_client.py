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

"""Agent Engine client for calling the code review agent."""

import json
import logging
import threading
import time

import vertexai
from config import Config
from vertexai import agent_engines

logger = logging.getLogger(__name__)


class AgentEngineClient:
    """Client for calling the deployed Agent Engine."""

    def __init__(self):
        """Initialize Agent Engine client."""
        vertexai.init(
            project=Config.GCP_PROJECT_ID,
            location=Config.GCP_REGION,
        )

        # Use project number from deployment metadata
        resource_name = f"projects/442593217095/locations/{Config.GCP_REGION}/reasoningEngines/{Config.AGENT_ENGINE_ID}"
        self.agent = agent_engines.get(resource_name=resource_name)
        logger.info("Agent Engine client initialized")

    def review_pr(self, review_context: dict, timeout_seconds: int = 600) -> dict:
        """Call the Agent Engine to review a PR.

        Args:
            review_context: Dictionary matching CodeReviewInput schema
            timeout_seconds: Maximum time to wait for response

        Returns:
            Dictionary containing review response
        """
        try:
            logger.info("Calling Agent Engine for code review")
            message_payload = json.dumps(review_context)
            logger.debug(
                f"Payload size: {len(message_payload.encode('utf-8')):,} bytes"
            )

            # Use stream_query for better handling
            response_chunks = []
            chunk_count = [0]
            last_chunk_time = [time.time()]
            stream_start_time = time.time()
            streaming_complete = threading.Event()
            stream_error: list[Exception | None] = [None]

            def stream_worker():
                """Worker thread to handle streaming."""
                try:
                    logger.debug("Starting agent stream query")
                    stream_iterator = self.agent.stream_query(
                        message=message_payload,
                        user_id="github-app-pr-review",
                    )

                    for chunk in stream_iterator:
                        chunk_count[0] += 1
                        last_chunk_time[0] = time.time()
                        response_chunks.append(chunk)

                        if chunk_count[0] % 10 == 0:
                            elapsed = time.time() - stream_start_time
                            logger.debug(
                                f"Received {chunk_count[0]} chunks (elapsed: {elapsed:.1f}s)"
                            )

                    logger.debug("Stream iteration completed")
                except Exception as e:
                    logger.error(f"Error in stream worker: {e}")
                    stream_error[0] = e
                finally:
                    streaming_complete.set()

            # Start streaming in a thread
            stream_thread = threading.Thread(target=stream_worker, daemon=True)
            stream_thread.start()

            # Monitor with timeout
            while not streaming_complete.is_set():
                elapsed = time.time() - stream_start_time
                if elapsed > timeout_seconds:
                    raise TimeoutError(
                        f"Stream query timed out after {timeout_seconds}s "
                        f"(received {chunk_count[0]} chunks)"
                    )

                streaming_complete.wait(timeout=5.0)

            # Check for errors
            if stream_error[0]:
                raise stream_error[0]

            stream_thread.join(timeout=5.0)

            if not response_chunks:
                raise Exception("No response chunks received from agent")

            logger.info(f"Received {len(response_chunks)} chunks from agent")

            # Extract structured output from chunks
            structured_output = None
            all_text_parts = []
            all_state_deltas = {}

            for chunk in response_chunks:
                # Collect text
                if hasattr(chunk, "content") and chunk.content:
                    if hasattr(chunk.content, "parts") and chunk.content.parts:
                        for part in chunk.content.parts:
                            if hasattr(part, "text") and part.text:
                                all_text_parts.append(part.text)

                # Collect structured data
                if hasattr(chunk, "actions") and chunk.actions:
                    if (
                        hasattr(chunk.actions, "state_delta")
                        and chunk.actions.state_delta
                    ):
                        all_state_deltas.update(chunk.actions.state_delta)

            # Look for structured output
            if "code_review_output" in all_state_deltas:
                structured_output = all_state_deltas["code_review_output"]
            elif "formatted_output" in all_state_deltas:
                structured_output = all_state_deltas["formatted_output"]
            else:
                for key in all_state_deltas:
                    if (
                        "output" in key.lower() or "review" in key.lower()
                    ) and isinstance(all_state_deltas[key], dict | list):
                        structured_output = all_state_deltas[key]
                        break

            # Use structured output if found
            if structured_output:
                if isinstance(structured_output, dict):
                    if (
                        "overall_status" in structured_output
                        or "summary" in structured_output
                    ):
                        logger.info("Using structured output from agent state")
                        return structured_output
                elif isinstance(structured_output, str):
                    try:
                        parsed = json.loads(structured_output)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass

            # Fallback to text response
            combined_text = "\n".join(all_text_parts).strip()
            if combined_text:
                logger.info("Using text response from agent")
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

            # Last resort
            raise Exception(
                f"Failed to extract response from {len(response_chunks)} chunks"
            )

        except Exception as e:
            logger.error(f"Agent Engine call failed: {e}", exc_info=True)
            raise Exception(f"Agent Engine call failed: {e}") from e
