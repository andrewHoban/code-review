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

"""
End-to-end tests that make real API calls to Gemini models.

These tests are slow and should only be run manually or in CI with proper rate limiting.
Use pytest -m "e2e" to run these tests, or pytest -m "not e2e" to skip them.
"""

import json
from pathlib import Path

import pytest
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.agents.python_review_pipeline import python_review_pipeline
from app.models.input_schema import (
    ChangedFile,
    CodeReviewInput,
    PullRequestMetadata,
    RepositoryInfo,
    ReviewContext,
)


@pytest.fixture
def sample_python_code() -> str:
    """Sample Python code for testing."""
    return """def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
"""


@pytest.fixture
def minimal_python_pr_input(sample_python_code: str) -> CodeReviewInput:
    """Minimal PR input for Python review."""
    return CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=1,
            repository="test/repo",
            title="Test PR",
            description="Test description",
            author="test_user",
            base_branch="main",
            head_branch="feature",
        ),
        review_context=ReviewContext(
            changed_files=[
                ChangedFile(
                    path="src/calc.py",
                    language="python",
                    status="added",
                    additions=10,
                    deletions=0,
                    diff="@@ -0,0 +1,10 @@\n" + sample_python_code,
                    full_content=sample_python_code,
                    lines_changed=list(range(1, 11)),
                )
            ],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(
                name="repo",
                primary_language="python",
                languages_used=["python"],
                total_files=10,
                has_tests=False,
            ),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_python_pipeline_e2e_structure_analysis(
    minimal_python_pr_input: CodeReviewInput,
) -> None:
    """
    E2E test: Python pipeline performs structure analysis with real API calls.

    This test makes real API calls to Gemini models and should only be run:
    - Manually when needed
    - In CI with proper rate limiting
    - With pytest -m "e2e"
    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(
        agent=python_review_pipeline, session_service=session_service, app_name="test"
    )

    # Convert input to message
    input_json = minimal_python_pr_input.model_dump_json()
    message = types.Content(role="user", parts=[types.Part.from_text(text=input_json)])

    # Run pipeline
    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    # Verify we got responses
    assert len(events) > 0, "Expected at least one event from pipeline"

    # Check that structure analysis was performed
    final_session = await session_service.get_session(
        user_id="test_user", session_id=session.id, app_name="test"
    )
    final_state = final_session.state

    # Verify specific expected state key exists and has meaningful content
    assert "python_structure_analysis_summary" in final_state
    analysis = final_state["python_structure_analysis_summary"]
    assert isinstance(analysis, str)
    assert (
        len(analysis) > 50
    ), "Analysis should contain meaningful content, not just empty string"
    # Verify it mentions something about the code structure
    analysis_lower = analysis.lower()
    assert any(
        keyword in analysis_lower
        for keyword in ["function", "class", "calculator", "add", "multiply"]
    ), "Analysis should mention code elements from the input"


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_python_pipeline_e2e_with_fixture() -> None:
    """
    E2E test: Python pipeline with real payload from fixtures.

    This test makes real API calls and should only be run manually or in CI.
    """
    # Load fixture
    fixture_path = Path(__file__).parent.parent / "fixtures" / "python_simple_pr.json"
    if not fixture_path.exists():
        pytest.skip("Fixture file not found")

    with open(fixture_path) as f:
        payload_data = json.load(f)

    input_data = CodeReviewInput.model_validate(payload_data)

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(
        agent=python_review_pipeline, session_service=session_service, app_name="test"
    )

    input_json = input_data.model_dump_json()
    message = types.Content(role="user", parts=[types.Part.from_text(text=input_json)])

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    # Verify pipeline completed
    assert len(events) > 0, "Expected at least one event from pipeline"

    # Check final state has analysis results
    final_session = await session_service.get_session(
        user_id="test_user", session_id=session.id, app_name="test"
    )
    final_state = final_session.state

    # Should have structure analysis with valid content
    assert "python_structure_analysis_summary" in final_state
    analysis = final_state["python_structure_analysis_summary"]
    assert isinstance(analysis, str)
    assert len(analysis) > 50, "Analysis should contain meaningful content"


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_root_agent_language_routing_python() -> None:
    """
    E2E test: Root agent routes Python files correctly with real API calls.

    This test makes real API calls and should only be run manually or in CI.
    """
    python_pr = CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=1,
            repository="test/repo",
            title="Python PR",
            author="dev",
            base_branch="main",
            head_branch="feature",
        ),
        review_context=ReviewContext(
            changed_files=[
                ChangedFile(
                    path="src/main.py",
                    language="python",
                    status="modified",
                    additions=5,
                    deletions=2,
                    diff="@@ -1,3 +1,6 @@\ndef hello():\n    print('Hello')\n",
                    full_content="def hello():\n    print('Hello')\n    return True\n",
                    lines_changed=[1, 2, 3],
                )
            ],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(
                name="repo",
                primary_language="python",
                languages_used=["python"],
                total_files=10,
                has_tests=True,
            ),
        ),
    )

    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    input_json = python_pr.model_dump_json()
    message = types.Content(role="user", parts=[types.Part.from_text(text=input_json)])

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    # Verify we got responses
    assert len(events) > 0, "Expected at least one event from agent"

    # Check that language was detected
    final_session = await session_service.get_session(
        user_id="test_user", session_id=session.id, app_name="test"
    )
    final_state = final_session.state

    # Verify language detection state
    assert (
        "detected_languages" in final_state or "language_files_map" in final_state
    ), "Language detection should store results in state"


@pytest.mark.skip(
    reason="Makes real API calls to Gemini - skip in CI to avoid rate limits"
)
@pytest.mark.asyncio
@pytest.mark.e2e
def test_agent_stream() -> None:
    """
    E2E test: Agent stream functionality with real API calls.

    Tests that the agent returns valid streaming responses.
    Note: This test makes real API calls to Gemini models and may hit rate limits.
    Run manually when needed, or use pytest -m "not e2e" to skip.
    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Why is the sky blue?")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    assert len(events) > 0, "Expected at least one message"

    has_text_content = False
    for event in events:
        if (
            event.content
            and event.content.parts
            and any(part.text for part in event.content.parts)
        ):
            has_text_content = True
            break
    assert has_text_content, "Expected at least one message with text content"
