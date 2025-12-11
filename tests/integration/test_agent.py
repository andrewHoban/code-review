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
from app.agents.python_review_pipeline import python_review_pipeline
from app.agents.typescript_review_pipeline import typescript_review_pipeline


def test_root_agent_has_correct_structure() -> None:
    """Test that root agent is configured correctly."""
    assert root_agent.name == "CodeReviewOrchestrator"
    assert root_agent.description is not None
    if isinstance(root_agent.description, str):
        assert len(root_agent.description) > 0
    assert root_agent.instruction is not None
    if isinstance(root_agent.instruction, str):
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


def test_root_agent_has_language_detection_tool() -> None:
    """Test that root agent has language detection tool."""
    tool_names = [tool.name for tool in root_agent.tools]
    assert any(
        "detect" in name.lower() or "language" in name.lower() for name in tool_names
    )


def test_root_agent_has_sub_agents() -> None:
    """Test that root agent has sub-agents for language pipelines."""
    assert len(root_agent.sub_agents) > 0
    sub_agent_names = [agent.name for agent in root_agent.sub_agents]
    assert any("python" in name.lower() for name in sub_agent_names)
    assert any("typescript" in name.lower() for name in sub_agent_names)


def test_python_pipeline_is_sequential_agent() -> None:
    """Test that Python pipeline is a sequential agent."""
    from google.adk.agents import SequentialAgent

    assert isinstance(python_review_pipeline, SequentialAgent)
    assert python_review_pipeline.name is not None
    assert "python" in python_review_pipeline.name.lower()


def test_python_pipeline_has_sub_agents() -> None:
    """Test that Python pipeline has the expected sub-agents."""
    assert len(python_review_pipeline.sub_agents) > 0
    sub_agent_names = [agent.name for agent in python_review_pipeline.sub_agents]
    # OPTIMIZED: Now has 2 agents instead of 4 (consolidated for token efficiency)
    # CodeAnalyzer (structure + design + style) and FeedbackReviewer (test + synthesis)
    assert any("analyzer" in name.lower() for name in sub_agent_names)
    assert any(
        "feedback" in name.lower() or "reviewer" in name.lower()
        for name in sub_agent_names
    )
    # Should have exactly 2 agents after optimization
    assert len(sub_agent_names) == 2


def test_typescript_pipeline_is_sequential_agent() -> None:
    """Test that TypeScript pipeline is a sequential agent."""
    from google.adk.agents import SequentialAgent

    assert isinstance(typescript_review_pipeline, SequentialAgent)
    assert typescript_review_pipeline.name is not None
    assert "typescript" in typescript_review_pipeline.name.lower()


def test_typescript_pipeline_has_sub_agents() -> None:
    """Test that TypeScript pipeline has the expected sub-agents."""
    assert len(typescript_review_pipeline.sub_agents) > 0
    sub_agent_names = [agent.name for agent in typescript_review_pipeline.sub_agents]
    # OPTIMIZED: Now has 2 agents instead of 4 (consolidated for token efficiency)
    # CodeAnalyzer (structure + design + style) and FeedbackReviewer (test + synthesis)
    assert any("analyzer" in name.lower() for name in sub_agent_names)
    assert any(
        "feedback" in name.lower() or "reviewer" in name.lower()
        for name in sub_agent_names
    )
    # Should have exactly 2 agents after optimization
    assert len(sub_agent_names) == 2


def test_python_pipeline_agents_have_tools() -> None:
    """Test that Python pipeline agents have the required tools."""
    for agent in python_review_pipeline.sub_agents:
        # First agent (analyzer) should have analysis tool
        if "analyzer" in agent.name.lower() and "test" not in agent.name.lower():
            assert (
                hasattr(agent, "tools") and len(agent.tools) > 0
            ), f"{agent.name} should have tools"
        # Style checker should have style tool
        if "style" in agent.name.lower():
            assert (
                hasattr(agent, "tools") and len(agent.tools) > 0
            ), f"{agent.name} should have tools"


def test_agent_output_keys_are_configured() -> None:
    """Test that agents have output keys configured."""
    assert root_agent.output_key is not None
    # Sequential agents don't have output_key attribute, which is expected
    assert not hasattr(python_review_pipeline, "output_key")
    # But sub-agents should have output keys
    for agent in python_review_pipeline.sub_agents:
        assert (
            hasattr(agent, "output_key") and agent.output_key is not None
        ), f"{agent.name} should have an output_key"
