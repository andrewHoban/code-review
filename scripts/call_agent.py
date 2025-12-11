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
) -> dict[str, Any]:
    """Call agent with exponential backoff retry."""
    vertexai.init(project=project_id, location=location)

    resource_name = (
        f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
    )

    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            # Get the deployed agent
            agent = agent_engines.get(resource_name=resource_name)

            # Query the agent with the payload as input
            user_id = f"pr-review-{payload.get('pr_metadata', {}).get('pr_number', 'unknown')}"
            response = agent.query(message=json.dumps(payload), user_id=user_id)

            # Parse response - the response format may vary
            # Try to extract text from the response
            response_text = None
            if isinstance(response, str):
                response_text = response
            elif hasattr(response, "text"):
                response_text = response.text
            elif hasattr(response, "content"):
                response_text = response.content
            elif hasattr(response, "response"):
                response_text = response.response
            else:
                response_text = str(response)

            # Try to parse as JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If not JSON, wrap it in a summary field
                return {
                    "summary": response_text,
                    "inline_comments": [],
                    "overall_status": "COMMENT",
                    "metrics": {},
                }

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
        )

        # Write output
        with open(args.output, "w") as f:
            json.dump(response, f, indent=2)

        print(f"Agent response written to: {args.output}")
        print(f"Status: {response.get('overall_status', 'UNKNOWN')}")
        print(f"Issues found: {response.get('metrics', {}).get('issues_found', 0)}")

    except Exception as e:
        print(f"Error calling agent: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
