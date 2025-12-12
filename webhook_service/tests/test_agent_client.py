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

"""Tests for Agent Engine client."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_client import AgentEngineClient


@pytest.fixture
def mock_agent_engine():
    """Mock Agent Engine."""
    mock_agent = Mock()

    # Mock stream query response
    mock_chunk = Mock()
    mock_chunk.content = Mock()
    mock_chunk.content.parts = [Mock(text="Review summary")]
    mock_chunk.actions = Mock()
    mock_chunk.actions.state_delta = {
        "code_review_output": {
            "summary": "## Review Summary",
            "inline_comments": [],
            "overall_status": "COMMENT",
        }
    }

    mock_agent.stream_query.return_value = [mock_chunk]

    return mock_agent


def test_review_pr(mock_agent_engine):
    """Test reviewing a PR."""
    with (
        patch("agent_client.vertexai.init"),
        patch("agent_client.agent_engines.get", return_value=mock_agent_engine),
    ):
        client = AgentEngineClient()

        review_context = {
            "pr_metadata": {"pr_number": 1},
            "review_context": {"changed_files": []},
        }

        response = client.review_pr(review_context)

        assert "summary" in response or "overall_status" in response
        assert mock_agent_engine.stream_query.called


def test_review_pr_timeout(mock_agent_engine):
    """Test PR review timeout handling."""
    # Mock stream that never completes
    import time

    def slow_stream():
        time.sleep(10)  # Simulate slow response
        yield Mock()

    mock_agent_engine.stream_query.return_value = slow_stream()

    with (
        patch("agent_client.vertexai.init"),
        patch("agent_client.agent_engines.get", return_value=mock_agent_engine),
    ):
        client = AgentEngineClient()

        review_context = {
            "pr_metadata": {"pr_number": 1},
            "review_context": {"changed_files": []},
        }

        with pytest.raises((TimeoutError, Exception)):  # Should timeout or raise error
            client.review_pr(review_context, timeout_seconds=1)
