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

from app.agent import root_agent


def test_root_agent_has_correct_structure() -> None:
    """Test that root agent is configured correctly."""
    # root_agent is now a ModelFallbackAgent wrapper
    assert root_agent.name == "CodeReviewerWithFallback"
    # ModelFallbackAgent has primary_agent and fallback_agent attributes
    assert hasattr(root_agent, "primary_agent")
    assert hasattr(root_agent, "fallback_agent")
    # Verify the wrapped agents are properly configured
    assert root_agent.primary_agent.name == "CodeReviewer"
    assert root_agent.fallback_agent.name == "CodeReviewer"


def test_agent_output_key_is_configured() -> None:
    """Test that root agent has output key configured."""
    # Check that wrapped agents have output_key configured
    assert root_agent.primary_agent.output_key is not None
    assert root_agent.primary_agent.output_key == "code_review_output"
    assert root_agent.fallback_agent.output_key == "code_review_output"
