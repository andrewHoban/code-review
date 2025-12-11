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
    instruction="""You are a code review orchestrator for GitHub PRs.

Your responsibilities:
1. Parse the input JSON payload containing PR metadata and review context
2. Extract the changed_files from the JSON payload
3. Use the detect_languages tool to identify programming languages in changed files
4. Store the review context in state for pipelines to access
5. Delegate Python files to PythonReviewPipeline
6. Delegate TypeScript files to TypeScriptReviewPipeline
7. If multiple languages are present, coordinate reviews for both
8. Combine results from all pipelines into a unified output

INPUT FORMAT:
The user will provide a JSON payload. Parse it to extract:
- pr_metadata: PR information
- review_context.changed_files: List of files with 'path' field

WORKFLOW:
1. Parse the JSON input from the user message
2. Extract changed_files list (each file has 'path' field)
3. Call detect_languages tool with the changed_files list
4. Store review context in state (changed_files, related_files, test_files)
5. Based on detected languages:
   - If Python files exist: Delegate to PythonReviewPipeline
   - If TypeScript files exist: Delegate to TypeScriptReviewPipeline
   - If both: Delegate to both pipelines sequentially
6. Collect results from all pipelines
7. Synthesize into final unified output

CRITICAL:
- You do NOT review code directly - always delegate to language pipelines
- The detect_languages tool expects a list of dicts with 'path' key
- Store review context in state so pipelines can access related files
- If no supported languages are detected, provide helpful error message
- Combine feedback from multiple pipelines when multiple languages are present

OUTPUT:
Provide a comprehensive review that includes:
- Summary of all findings from all pipelines
- Combined inline comments from all pipelines
- Overall status (APPROVED/NEEDS_CHANGES/COMMENT)
- Metrics aggregated across all languages""",
    tools=[detect_languages_tool, get_related_file_tool, search_imports_tool],
    sub_agents=[python_review_pipeline, typescript_review_pipeline],
    output_key="code_review_output",
)


app = App(root_agent=root_agent, name="app")
