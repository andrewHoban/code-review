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
import os
import sys
import threading
import time
from typing import Any

import vertexai
from vertexai import agent_engines

from app.utils.stream_extractor import coerce_review_output, extract_text_and_state


def _is_resource_exhausted_error(err: Exception) -> bool:
    msg = str(err)
    return ("RESOURCE_EXHAUSTED" in msg) or ("429" in msg)


def _resource_exhausted_response(err: Exception) -> dict[str, Any]:
    # User asked for explicit messaging rather than generic fallback.
    return {
        "summary": (
            "**Code review failed due to company token/quota restrictions (429 RESOURCE_EXHAUSTED).**\n\n"
            "This run could not complete because Vertex AI rate-limited the model call.\n\n"
            "- **What to do**: re-run later, reduce PR payload size, or request higher quota.\n"
            "- **Diagnostic**: check Agent Engine logs for `RESOURCE_EXHAUSTED` / `429`."
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
        "error": {
            "type": type(err).__name__,
            "message": str(err),
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
        },
    }


def _safe_jsonable(obj: Any) -> Any:
    """Best-effort conversion to JSON-able structure for debug dumps."""
    if obj is None:
        return None
    if isinstance(obj, str | int | float | bool):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_jsonable(v) for v in obj]
    # ADK / pydantic-ish
    for method in ("model_dump", "to_dict"):
        fn = getattr(obj, method, None)
        if callable(fn):
            try:
                return _safe_jsonable(fn())
            except Exception:
                pass
    return {"__type__": str(type(obj)), "__repr__": repr(obj)[:2000]}


def _debug_dump_chunks(chunks: list[Any], output_path: str) -> None:
    """Write a JSONL debug dump of chunks (bounded, safe)."""
    try:
        with open(output_path, "w") as f:
            for i, chunk in enumerate(chunks):
                record = {
                    "i": i,
                    "type": str(type(chunk)),
                    "chunk": _safe_jsonable(chunk),
                }
                f.write(json.dumps(record) + "\n")
        print(f"Debug: wrote chunk dump to {output_path}")
    except Exception as e:
        print(f"Debug: failed to write chunk dump: {e}")


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

            def stream_worker() -> None:
                """Worker thread to handle streaming with timeout detection."""
                nonlocal \
                    response_chunks, \
                    chunk_count, \
                    last_chunk_time, \
                    stream_error, \
                    agent, \
                    message_payload, \
                    stream_start_time
                try:
                    print("  Invoking agent.stream_query()...")
                    stream_iterator = agent.stream_query(  # noqa: B023
                        message=message_payload,  # noqa: B023
                        user_id="github-actions-pr-review",
                    )
                    print("  Stream iterator created, starting iteration...")

                    for chunk in stream_iterator:
                        chunk_count[0] += 1  # noqa: B023
                        last_chunk_time[0] = time.time()  # noqa: B023
                        response_chunks.append(chunk)  # noqa: B023

                        # Log progress every 10 chunks or if we can extract text
                        if chunk_count[0] % 10 == 0 or chunk_count[0] == 1:  # noqa: B023
                            elapsed = time.time() - stream_start_time  # noqa: B023
                            chunk_info = "chunk"
                            if hasattr(chunk, "text") and chunk.text:
                                preview = chunk.text[:100].replace("\n", " ")
                                chunk_info = f"chunk with text: {preview}..."
                            elif isinstance(chunk, str):
                                preview = chunk[:100].replace("\n", " ")
                                chunk_info = f"chunk (str): {preview}..."
                            elif isinstance(chunk, dict):
                                # Check for state delta or content in dict
                                if "actions" in chunk or "state_delta" in chunk:
                                    chunk_info = "chunk with state_delta"
                                elif "content" in chunk or "text" in chunk:
                                    chunk_info = "chunk with content"
                                else:
                                    chunk_info = (
                                        f"chunk (dict): {list(chunk.keys())[:3]}"
                                    )
                            else:
                                chunk_info = f"chunk (type: {type(chunk).__name__})"
                            print(
                                f"  Received {chunk_count[0]} chunks (elapsed: {elapsed:.1f}s) - latest: {chunk_info}"  # noqa: B023
                            )

                    print("  Stream iteration completed normally.")
                except Exception as e:
                    print(f"  Error in stream worker: {type(e).__name__}: {e}")
                    stream_error[0] = e  # noqa: B023
                finally:
                    streaming_complete.set()  # noqa: B023

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
                print("\n" + "=" * 80)
                print("ERROR: No response chunks received from agent stream.")
                print("=" * 80)
                print(
                    "Possible causes:\n"
                    "1) Agent completed but produced no text output (only state updates)\n"
                    "2) Agent failed silently without producing output\n"
                    "3) Streaming API issue or agent deployment problem\n"
                    "4) Agent instruction may need to explicitly require text output\n"
                )
                print(
                    "Diagnostic steps:\n"
                    "- Check Agent Engine logs in GCP Console for errors\n"
                    "- Verify agent is deployed and accessible\n"
                    "- Check if agent instruction requires text output (not just state updates)\n"
                    "- Review agent configuration and model availability\n"
                )
                print("=" * 80 + "\n")
                # Raise exception with actionable error message
                raise Exception(
                    "No response chunks received from agent after successful stream completion. "
                    "The agent stream completed normally but produced no chunks. "
                    "This typically means the agent updated state but didn't produce streamable text output. "
                    "Check Agent Engine logs and verify the publisher agent instruction requires text output."
                )

            print(
                f"\nProcessing {len(response_chunks)} chunks to extract final response..."
            )

            debug_dump_path = os.environ.get("CODE_REVIEW_DUMP_CHUNKS")
            if debug_dump_path:
                _debug_dump_chunks(response_chunks, debug_dump_path)

            combined_text, merged_state = extract_text_and_state(response_chunks)
            print(
                f"Debug: Extracted text length={len(combined_text)}, "
                f"state_delta_keys={list(merged_state.keys())}"
            )

            # Add performance metrics to state
            merged_state["performance_metrics"] = {
                "review_duration_seconds": elapsed_total,
                "chunks_received": chunk_count[0],
                "payload_size_bytes": payload_size,
            }

            return coerce_review_output(combined_text, merged_state)

        except Exception as e:
            last_error = e
            if _is_resource_exhausted_error(e):
                # Don't hide quota issues behind a generic fallback: return an explicit result
                # so the workflow can post a meaningful comment.
                print(
                    f"Detected quota/resource exhaustion error: {type(e).__name__}: {e}"
                )
                return _resource_exhausted_response(e)
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
