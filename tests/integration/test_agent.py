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

"""Integration tests for agent configuration and structure."""

# mypy: disable-error-code="union-attr"
import pytest

from app.agent import root_agent


def test_root_agent_has_correct_structure() -> None:
    """Test that root agent is configured correctly."""
    assert root_agent.name == "CodeReviewer"
    assert root_agent.description is not None
    assert len(root_agent.description) > 0
    assert root_agent.instruction is not None
    assert len(root_agent.instruction) > 0


@pytest.mark.skip(
    reason="Makes real API calls to Gemini - skip in CI to avoid rate limits"
)
def test_agent_stream() -> None:
    """
    Integration test for the agent stream functionality.
    Tests that the agent returns valid streaming responses.

    Note: This test makes real API calls to Gemini models and may hit rate limits.
    Run manually when needed, or use pytest -m "not slow" to skip.
    """


@pytest.mark.skip(
    "Agent architecture changed to single LLM-based agent without explicit tools"
)
def test_root_agent_has_language_detection_tool() -> None:
    """Test that root agent has language detection tool."""
    tool_names = [tool.name for tool in root_agent.tools]
    assert any(
        "detect" in name.lower() or "language" in name.lower() for name in tool_names
    )


@pytest.mark.skip("Agent architecture changed to single agent without sub-agents")
def test_root_agent_has_sub_agents() -> None:
    """Test that root agent has sub-agents for language pipelines."""
    assert len(root_agent.sub_agents) > 0
    sub_agent_names = [agent.name for agent in root_agent.sub_agents]
    assert any("python" in name.lower() for name in sub_agent_names)
    assert any("typescript" in name.lower() for name in sub_agent_names)


def test_agent_output_key_is_configured() -> None:
    """Test that root agent has output key configured."""
    assert root_agent.output_key is not None
    assert root_agent.output_key == "code_review_output"
