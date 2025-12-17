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

import logging
import os
from typing import Any

import google.auth
from google.adk.agents import Agent
from google.adk.apps.app import App

from app.config import LANGUAGE_DETECTOR_MODEL, LANGUAGE_DETECTOR_FALLBACK_MODEL
from app.models.output_schema import CodeReviewOutput
from app.prompts.static_context import STATIC_REVIEW_CONTEXT

logger = logging.getLogger(__name__)


# Note: Model fallback is configured in app/config.py
# Primary: gemini-2.5-pro
# Fallback: publishers/google/models/llama-4 (free, good quality)
#
# Agent-level fallback requires Plugin support which isn't easily available in AgentEngineApp.
# The fallback model will be used automatically when the primary model hits token/quota limits
# via the retry mechanism in scripts/call_agent.py or by Vertex AI's built-in retry logic.


_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# Single agent that reviews code directly using LLM reasoning
# Uses structured output via response_schema to guarantee valid JSON
# Fallback to Llama 4 is configured in app/config.py and handled by retry logic
root_agent = Agent(
    name="CodeReviewer",
    model=LANGUAGE_DETECTOR_MODEL,  # gemini-2.5-pro (falls back to publishers/google/models/llama-4 on token/quota errors)
    description="Expert code reviewer for GitHub PRs using comprehensive review principles",
    instruction=f"""{STATIC_REVIEW_CONTEXT}

You are an expert code reviewer analyzing GitHub pull requests.

INPUT FORMAT:
You'll receive JSON with:
- pr_metadata: PR title, description, author
- review_context.changed_files: Files with diffs, full_content, language
- review_context.related_files: Context from related files
- review_context.test_files: Test coverage

YOUR TASK:
1. Read all changed files and their full content
2. Apply the review principles above to the code
3. Check for: Correctness, Security, Performance, Design, Test quality
4. Return a structured JSON response with your findings

OUTPUT STRUCTURE:
- summary: Overall review summary in markdown (use "LGTM - no significant issues." if clean)
- overall_status: One of ["APPROVED", "NEEDS_CHANGES", "COMMENT"]
  - APPROVED: No issues or only minor suggestions
  - NEEDS_CHANGES: Has HIGH severity issues
  - COMMENT: Has MEDIUM severity issues worth noting
- inline_comments: Array of specific line comments (empty if no issues)
  - path: File path
  - line: Line number
  - severity: One of ["error", "warning", "info", "suggestion"]
  - body: Comment in markdown with issue + fix suggestion
- metrics: Review statistics
  - files_reviewed: Number of files reviewed
  - issues_found: Total issues count
  - critical_issues: HIGH severity count
  - warnings: MEDIUM severity count
  - suggestions: LOW severity count

CRITICAL REMINDERS:
- 60-80% of PRs should mostly pass - be constructive, not harsh
- Be specific with file:line references in inline_comments
- Use "APPROVED" liberally when code is clean
- No praise, no "what went well" sections, no congratulations
- Focus exclusively on issues that need addressing
""",
    output_key="code_review_output",
    output_schema=CodeReviewOutput,  # ADK will automatically configure Gemini's response_schema
    generate_content_config={
        "temperature": 0.3,
        "max_output_tokens": 8192,
    },
)


app = App(root_agent=root_agent, name="app")
