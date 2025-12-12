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
4. Produce a structured markdown review following the format below

OUTPUT FORMAT (markdown):

## Summary
One sentence overall assessment. Use "LGTM - no significant issues." if code is clean.

## Correctness & Security
List only HIGH severity issues (expect 0-2 per review).
Format: **Issue Title** - File:line - Description - How to fix
If none found: "LGTM"

## Design & Maintainability
List only MEDIUM severity issues, top 5 by impact.
Format: **Issue Title** - File:line - Description
If none found: "LGTM"

## Test Coverage
Note critical gaps only (auth, payment, data loss scenarios).
If adequate: "LGTM"

## Issues to Address
Numbered list combining HIGH and top MEDIUM issues only.
Skip this section entirely if no issues.

CRITICAL REMINDERS:
- 60-80% of PRs should mostly pass - be constructive, not harsh
- Be specific with file:line references and show code snippets for HIGH issues
- Use "LGTM" liberally when sections are clean
- No praise, no "what went well" sections, no congratulations
- Focus exclusively on issues that need addressing
- If everything is acceptable, keep it brief with "LGTM"
""",
    output_key="code_review_output",
)


app = App(root_agent=root_agent, name="app")
