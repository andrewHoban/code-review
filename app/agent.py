# ruff: noqa
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

import json
import logging
import os

import google.auth
from google.adk.agents import Agent
from google.adk.apps.app import App

from app.agents.python_review_pipeline import python_review_pipeline
from app.agents.typescript_review_pipeline import typescript_review_pipeline
from app.config import LANGUAGE_DETECTOR_MODEL
from app.tools.language_detection import detect_languages_tool
from app.tools.repo_context import (
    RepoContextStateKeys,
    get_related_file_tool,
    search_imports_tool,
)
from app.utils.input_preparation import (
    parse_review_input,
    prepare_changed_files_for_detection,
    store_review_context_in_state,
)

logger = logging.getLogger(__name__)

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# Root orchestrator agent that detects languages and routes to pipelines
# TODO: Consider adding support for additional languages in the future
root_agent = Agent(
    name="CodeReviewOrchestrator",
    model=LANGUAGE_DETECTOR_MODEL,
    description="Orchestrates code review by detecting languages and routing to appropriate pipelines",
    instruction="""Code review orchestrator for GitHub PRs.

Workflow:
1. Extract changed_files from user message (JSON with 'path' field)
2. Call detect_languages tool with changed_files list
3. Delegate to PythonReviewPipeline (if Python files) or TypeScriptReviewPipeline (if TS files)
4. Combine pipeline results into unified output

Rules:
- Use detect_languages tool (don't detect manually)
- Delegate to pipelines (don't review directly)
- No Python code execution
- Extract from message directly (don't parse JSON manually)

Output: Combine pipeline results. Use "LGTM" if no issues. Status: APPROVED/NEEDS_CHANGES/COMMENT. Be brief.""",
    tools=[detect_languages_tool, get_related_file_tool, search_imports_tool],
    sub_agents=[python_review_pipeline, typescript_review_pipeline],
    output_key="code_review_output",
)


app = App(root_agent=root_agent, name="app")
