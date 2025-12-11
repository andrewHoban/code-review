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
from google.adk.agents import Agent, SequentialAgent
from google.adk.apps.app import App

from app.agents.python_review_pipeline import python_review_pipeline
from app.agents.typescript_review_pipeline import typescript_review_pipeline
from app.config import ORCHESTRATOR_MODEL, PUBLISHER_MODEL
from app.utils.model_router import create_routed_agent
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


# Orchestrator agent that detects languages and routes to pipelines.
# This agent focuses on routing + delegating work; a final publisher agent
# is responsible for emitting a single, postable review output.
# Uses free model (Codestral) directly - simple routing task doesn't need Gemini 2.5 Pro
orchestrator_agent = create_routed_agent(
    name="CodeReviewOrchestrator",
    primary_model=ORCHESTRATOR_MODEL,
    description="Orchestrates code review by detecting languages and routing to appropriate pipelines",
    instruction="""Code review orchestrator for GitHub PRs.

Workflow:
1. Extract changed_files from user message (JSON with 'path' field)
2. Call detect_languages tool with changed_files list
3. Delegate to PythonReviewPipeline (if Python files) or TypeScriptReviewPipeline (if TS files)
4. Store results in state for the publisher agent to format

Rules:
- Use detect_languages tool (don't detect manually)
- Delegate to pipelines (don't review directly)
- No Python code execution
- Extract from message directly (don't parse JSON manually)

Output: Do NOT attempt to format final PR comment text. The publisher will do that.""",
    tools=[detect_languages_tool, get_related_file_tool, search_imports_tool],
    sub_agents=[python_review_pipeline, typescript_review_pipeline],
    # Keep orchestrator output separate from final review output.
    output_key="orchestrator_output",
)

# Final publisher agent: emits one JSON object with Markdown in `summary`.
# This keeps the GitHub posting side simple (extract final text + json.loads).
# Uses free model (Codestral) directly - simple JSON formatting doesn't need advanced reasoning
publisher_agent = create_routed_agent(
    name="ReviewPublisher",
    primary_model=PUBLISHER_MODEL,
    description="Formats the final PR review as a single JSON object containing Markdown summary",
    instruction="""You are the final publisher for an automated GitHub PR code review.

Your job: output EXACTLY ONE valid JSON object as plain text (no markdown code fences, no extra commentary).

You MUST read prior results from state:
- python_final_feedback (if present): markdown sections for Python changes
- typescript_final_feedback (if present): markdown sections for TypeScript changes
- pr_metadata (if present): contains title/description, etc.
- changed_files (if present): list of changed files
- model_fallbacks (if present): list of agents that used fallback models due to token limits

Output contract - return this exact JSON structure:
{
  "summary": "<markdown>",
  "inline_comments": [],
  "overall_status": "APPROVED" | "NEEDS_CHANGES" | "COMMENT",
  "metrics": {
    "files_reviewed": <int>,
    "issues_found": <int>,
    "critical_issues": <int>,
    "warnings": <int>,
    "suggestions": <int>,
    "style_score": <float>
  }
}

Rules:
- Always produce a meaningful `summary` even if upstream state is missing. If nothing is available, say you couldn't extract review details and suggest checking workflow logs.
- Prefer brevity and actionable feedback. If feedback indicates no issues, use: \"LGTM - no significant issues.\".
- Determine `overall_status` conservatively:
  - If upstream feedback contains HIGH severity issues, set NEEDS_CHANGES.
  - Else if it contains MEDIUM severity issues, set COMMENT.
  - Else set APPROVED.
- Set `inline_comments` to [] (no inline posting from the publisher).
- Metrics can be best-effort estimates; if unknown, use zeros except `files_reviewed` which should be len(changed_files) when available.

CRITICAL REQUIREMENT - YOU MUST OUTPUT TEXT:
Your response MUST contain the JSON object as actual text that will be streamed to the client. This is NOT optional.
Start your response immediately with the opening brace '{' of the JSON object.
Do NOT wrap it in markdown code fences (no ```json).
Do NOT add any explanatory text before or after the JSON.
The system will automatically save your output to state AND stream it to the client.
If you produce no text output, the agent will fail with "no response chunks received".

Example correct output:
{"summary": "## Code Review\\n\\nLGTM...", "inline_comments": [], "overall_status": "APPROVED", "metrics": {"files_reviewed": 3, "issues_found": 0, "critical_issues": 0, "warnings": 0, "suggestions": 2, "style_score": 9.5}}

If model_fallbacks is present in state, append a note to the summary explaining that open source fallback models were used due to Gemini token/quota limits. Format: 'Note: This review used open source fallback models ([list agent names]) due to Gemini token limits. Review quality may be slightly reduced.'""",
    # Don't use output_key - we need the JSON to be streamed as text, not just saved to state
    # The stream_extractor will parse the JSON from the streamed text
)

# Root agent is a short, deterministic chain: orchestrate → publish.
root_agent = SequentialAgent(
    name="CodeReviewRoot",
    description="Orchestrates review pipelines then publishes a final review output",
    sub_agents=[orchestrator_agent, publisher_agent],
)


app = App(root_agent=root_agent, name="app")
