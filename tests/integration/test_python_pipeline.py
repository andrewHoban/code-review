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

"""Integration tests for Python review pipeline."""

import json
from pathlib import Path

import pytest
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

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
@pytest.mark.integration
async def test_python_pipeline_structure_analysis(
    minimal_python_pr_input: CodeReviewInput,
) -> None:
    """Test that Python pipeline performs structure analysis."""
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
    assert len(events) > 0

    # Check that structure analysis was performed
    # Use async method to get session
    final_session = await session_service.get_session(
        user_id="test_user", session_id=session.id, app_name="test"
    )
    final_state = final_session.state
    # Verify specific expected state key exists and has content
    assert "python_structure_analysis_summary" in final_state
    analysis = final_state["python_structure_analysis_summary"]
    assert isinstance(analysis, str)
    assert len(analysis) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_python_pipeline_with_real_payload() -> None:
    """Test Python pipeline with real payload from fixtures."""
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
    assert len(events) > 0

    # Check final state has analysis results
    # Use async method to get session
    final_session = await session_service.get_session(
        user_id="test_user", session_id=session.id, app_name="test"
    )
    final_state = final_session.state
    # Should have structure analysis with valid content
    assert "python_structure_analysis_summary" in final_state
    analysis = final_state["python_structure_analysis_summary"]
    assert isinstance(analysis, str)
    assert len(analysis) > 0
