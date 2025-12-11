#!/usr/bin/env python3
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

"""Call the deployed code review agent via Agent Engine API."""

import argparse
import json
import sys
import threading
import time
from typing import Any

import vertexai
from vertexai import agent_engines


def call_agent_with_retry(
    payload: dict[str, Any],
    project_id: str,
    location: str,
    agent_engine_id: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    timeout_seconds: int = 600,  # 10 minutes default timeout
) -> dict[str, Any]:
    """Call agent with exponential backoff retry."""
    # Initialize vertexai
    vertexai.init(project=project_id, location=location)

    resource_name = (
        f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
    )

    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries}: Getting agent...")
            # Get the deployed agent using the direct module approach
            agent = agent_engines.get(resource_name=resource_name)
            print("Agent retrieved successfully. Starting stream query...")

            # Prepare message payload
            message_payload = json.dumps(payload)
            payload_size = len(message_payload.encode("utf-8"))
            print(f"Payload size: {payload_size:,} bytes")
            print(f"Payload preview: {message_payload[:200]}...")

            # Query the agent using stream_query with correct parameters
            # Note: stream_query requires 'message' (not 'input') and 'user_id'
            response_chunks = []
            chunk_count = [0]  # Use list for thread-safe access
            last_chunk_time = [time.time()]  # Use list for thread-safe access
            stream_start_time = time.time()

            # Create a flag to track if streaming is complete
            streaming_complete = threading.Event()
            stream_error: list[Exception | None] = [
                None
            ]  # Use list to allow modification from nested scope

            def stream_worker() -> None:  # noqa: B023
                """Worker thread to handle streaming with timeout detection."""
                nonlocal (
                    response_chunks,
                    chunk_count,
                    last_chunk_time,
                    stream_error,
                    agent,
                    message_payload,
                    stream_start_time,
                )
                try:
                    print("  Invoking agent.stream_query()...")
                    stream_iterator = agent.stream_query(
                        message=message_payload,
                        user_id="github-actions-pr-review",
                    )
                    print("  Stream iterator created, starting iteration...")

                    for chunk in stream_iterator:
                        chunk_count[0] += 1
                        last_chunk_time[0] = time.time()
                        response_chunks.append(chunk)

                        # Log progress every 10 chunks or if we can extract text
                        if chunk_count[0] % 10 == 0 or chunk_count[0] == 1:
                            elapsed = time.time() - stream_start_time
                            chunk_info = "chunk"
                            if hasattr(chunk, "text") and chunk.text:
                                preview = chunk.text[:100].replace("\n", " ")
                                chunk_info = f"chunk with text: {preview}..."
                            elif isinstance(chunk, str):
                                preview = chunk[:100].replace("\n", " ")
                                chunk_info = f"chunk (str): {preview}..."
                            print(
                                f"  Received {chunk_count[0]} chunks (elapsed: {elapsed:.1f}s) - latest: {chunk_info}"
                            )

                    print("  Stream iteration completed normally.")
                except Exception as e:
                    print(f"  Error in stream worker: {type(e).__name__}: {e}")
                    stream_error[0] = e
                finally:
                    streaming_complete.set()

            # Start streaming in a thread so we can monitor for timeouts
            stream_thread = threading.Thread(target=stream_worker, daemon=True)
            stream_thread.start()

            # Monitor the stream with timeout
            print(f"Streaming started (timeout: {timeout_seconds}s)...")
            while not streaming_complete.is_set():
                elapsed = time.time() - stream_start_time
                time_since_last_chunk = time.time() - last_chunk_time[0]

                # Check for timeout
                if elapsed > timeout_seconds:
                    raise TimeoutError(
                        f"Stream query timed out after {timeout_seconds}s "
                        f"(received {chunk_count[0]} chunks)"
                    )

                # Warn if no chunks received for a while
                if chunk_count[0] == 0 and elapsed > 30:
                    print(f"  Warning: No chunks received after {elapsed:.1f}s...")
                elif chunk_count[0] > 0 and time_since_last_chunk > 120:
                    print(
                        f"  Warning: No new chunks for {time_since_last_chunk:.1f}s "
                        f"(total chunks: {chunk_count[0]})..."
                    )

                # Check every 5 seconds
                streaming_complete.wait(timeout=5.0)

            # Check if there was an error in the stream
            if stream_error[0]:
                raise stream_error[0]

            # Wait for thread to finish
            stream_thread.join(timeout=5.0)

            elapsed_total = time.time() - stream_start_time
            print(
                f"Streaming completed: {chunk_count[0]} chunks received in {elapsed_total:.1f}s"
            )

            # Check if we received any response
            if not response_chunks:
                raise Exception("No response chunks received from agent")

            print(
                f"\nProcessing {len(response_chunks)} chunks to extract final response..."
            )

            # The agent returns streaming chunks - we need to find the final output
            # The output is typically in the last chunk's content.parts[0].text
            # or in the state_delta with the output_key

            final_output = None
            all_text_parts = []

            for i, chunk in enumerate(response_chunks):
                # Try to extract from content
                if hasattr(chunk, "content") and chunk.content:
                    if hasattr(chunk.content, "parts") and chunk.content.parts:
                        for part in chunk.content.parts:
                            if hasattr(part, "text") and part.text:
                                all_text_parts.append(part.text)

                # Try to extract from state_delta (output_key)
                if hasattr(chunk, "actions") and chunk.actions:
                    if (
                        hasattr(chunk.actions, "state_delta")
                        and chunk.actions.state_delta
                    ):
                        state_delta = chunk.actions.state_delta
                        # Check for the output key
                        if "code_review_output" in state_delta:
                            final_output = state_delta["code_review_output"]
                            print(f"Found code_review_output in chunk {i + 1}")
                        # Also check for direct output
                        for key in state_delta:
                            if "output" in key.lower() or "review" in key.lower():
                                if isinstance(state_delta[key], dict | list):
                                    final_output = state_delta[key]
                                    print(f"Found output in state_delta key: {key}")

            # If we found structured output in state, use it
            if final_output:
                if isinstance(final_output, dict):
                    return final_output
                elif isinstance(final_output, str):
                    try:
                        return json.loads(final_output)
                    except json.JSONDecodeError:
                        pass

            # Otherwise, try to parse the combined text
            combined_text = "\n".join(all_text_parts)

            if combined_text:
                print(f"Extracted {len(combined_text)} characters of text from chunks")
                # Try to parse as JSON
                try:
                    return json.loads(combined_text)
                except json.JSONDecodeError:
                    # If not JSON, wrap it in a human-readable format
                    return {
                        "summary": combined_text,
                        "inline_comments": [],
                        "overall_status": "COMMENT",
                        "metrics": {},
                    }

            # Last resort - try to extract anything from the final chunk
            final_chunk = response_chunks[-1]
            print("Falling back to final chunk extraction")
            print(f"Final chunk type: {type(final_chunk)}")
            print(
                f"Final chunk attributes: {[attr for attr in dir(final_chunk) if not attr.startswith('_')][:20]}"
            )

            # Try various extraction methods
            if isinstance(final_chunk, str):
                try:
                    return json.loads(final_chunk)
                except json.JSONDecodeError:
                    return {
                        "summary": final_chunk,
                        "inline_comments": [],
                        "overall_status": "COMMENT",
                        "metrics": {},
                    }
            elif isinstance(final_chunk, dict):
                return final_chunk
            else:
                raise Exception(
                    f"Failed to extract response from {len(response_chunks)} chunks. "
                    f"Last chunk type: {type(final_chunk)}"
                )

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"All {max_retries} attempts failed. Last error: {e}")
                raise

    raise last_error or Exception("Unknown error occurred")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Call code review agent")
    parser.add_argument("--payload", required=True, help="Input JSON payload file")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--project-id", required=True, help="GCP project ID")
    parser.add_argument("--location", required=True, help="GCP location/region")
    parser.add_argument("--agent-engine-id", required=True, help="Agent Engine ID")
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Maximum retry attempts"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds for agent response (default: 600)",
    )

    args = parser.parse_args()

    try:
        # Load payload
        with open(args.payload) as f:
            payload = json.load(f)

        print(
            f"Calling agent for PR #{payload.get('pr_metadata', {}).get('pr_number', 'unknown')}..."
        )

        # Call agent
        response = call_agent_with_retry(
            payload=payload,
            project_id=args.project_id,
            location=args.location,
            agent_engine_id=args.agent_engine_id,
            max_retries=args.max_retries,
            timeout_seconds=args.timeout,
        )

        # Write output
        with open(args.output, "w") as f:
            json.dump(response, f, indent=2)

        print(f"\n{'=' * 80}")
        print(f"Agent response written to: {args.output}")
        print(f"{'=' * 80}\n")

        # Display human-readable summary
        print("📋 REVIEW SUMMARY")
        print("-" * 80)

        if "summary" in response:
            print(response["summary"][:500])
            if len(response["summary"]) > 500:
                print(f"\n... (truncated, see {args.output} for full output)")

        print("\n📊 METRICS")
        print("-" * 80)
        print(f"Status: {response.get('overall_status', 'UNKNOWN')}")

        metrics = response.get("metrics", {})
        if metrics:
            print(f"Issues found: {metrics.get('issues_found', 0)}")
            print(f"Files reviewed: {metrics.get('files_reviewed', 0)}")
            print(f"Comments: {metrics.get('comments_count', 0)}")

        inline_comments = response.get("inline_comments", [])
        if inline_comments:
            print(f"\n💬 INLINE COMMENTS: {len(inline_comments)}")
            print("-" * 80)
            for i, comment in enumerate(inline_comments[:3], 1):
                print(
                    f"\n{i}. {comment.get('file', 'unknown')}:{comment.get('line', '?')}"
                )
                print(f"   {comment.get('comment', 'No comment')[:100]}...")

            if len(inline_comments) > 3:
                print(
                    f"\n... and {len(inline_comments) - 3} more (see {args.output} for full output)"
                )

        print(f"\n{'=' * 80}")

    except Exception as e:
        print(f"Error calling agent: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
