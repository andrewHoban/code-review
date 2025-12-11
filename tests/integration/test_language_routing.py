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

"""Integration tests for language detection and routing."""

import json
import pytest
from pathlib import Path

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.models.input_schema import (
    ChangedFile,
    CodeReviewInput,
    PullRequestMetadata,
    RepositoryInfo,
    ReviewContext,
)


@pytest.fixture
def python_only_pr():
    """PR with only Python files."""
    return CodeReviewInput(
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


@pytest.fixture
def typescript_only_pr():
    """PR with only TypeScript files."""
    return CodeReviewInput(
        pr_metadata=PullRequestMetadata(
            pr_number=2,
            repository="test/repo",
            title="TypeScript PR",
            author="dev",
            base_branch="main",
            head_branch="feature",
        ),
        review_context=ReviewContext(
            changed_files=[
                ChangedFile(
                    path="src/index.ts",
                    language="typescript",
                    status="modified",
                    additions=5,
                    deletions=2,
                    diff="@@ -1,3 +1,6 @@\nexport function hello() {\n  console.log('Hello');\n}\n",
                    full_content="export function hello(): void {\n  console.log('Hello');\n  return;\n}\n",
                    lines_changed=[1, 2, 3],
                )
            ],
            related_files=[],
            test_files=[],
            dependency_map={},
            repository_info=RepositoryInfo(
                name="repo",
                primary_language="typescript",
                languages_used=["typescript"],
                total_files=15,
                has_tests=True,
            ),
        ),
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_language_detection_python(python_only_pr):
    """Test that Python files are detected and routed correctly."""
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        user_id="test_user", app_name="test"
    )
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    input_json = python_only_pr.model_dump_json()
    message = types.Content(
        role="user", parts=[types.Part.from_text(text=input_json)]
    )

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

    # Check that language was detected
    # Use async method to get session
    final_session = await session_service.get_session(
        user_id="test_user", session_id=session.id, app_name="test"
    )
    final_state = final_session.state
    assert "detected_languages" in final_state or "language_files_map" in final_state


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_language_detection_typescript(typescript_only_pr):
    """Test that TypeScript files are detected and routed correctly."""
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(
        user_id="test_user", app_name="test"
    )
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    input_json = typescript_only_pr.model_dump_json()
    message = types.Content(
        role="user", parts=[types.Part.from_text(text=input_json)]
    )

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

    # Check that language was detected
    # Use async method to get session
    final_session = await session_service.get_session(
        user_id="test_user", session_id=session.id, app_name="test"
    )
    final_state = final_session.state
    assert "detected_languages" in final_state or "language_files_map" in final_state
