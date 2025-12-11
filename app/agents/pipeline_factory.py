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

"""Factory for creating language-specific review pipelines."""

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import FunctionTool

from app.config import (
    CODE_ANALYZER_MODEL,
    FEEDBACK_SYNTHESIZER_MODEL,
)
from app.prompts.core_principles import CORE_PRINCIPLES
from app.prompts.design_principles import DESIGN_PRINCIPLES
from app.prompts.static_context import STATIC_REVIEW_CONTEXT
from app.prompts.test_principles import TEST_PRINCIPLES


def create_review_pipeline(
    language: str,
    analyzer_tool: FunctionTool,
    style_tool: FunctionTool,
    structure_summary_key: str,
    style_summary_key: str,
    test_summary_key: str,
    final_feedback_key: str,
) -> SequentialAgent:
    """
    Create a language-specific code review pipeline.

    Args:
        language: Language name (e.g., "Python", "TypeScript")
        analyzer_tool: Tool for analyzing code structure
        style_tool: Tool for checking code style
        structure_summary_key: State key for structure analysis summary
        style_summary_key: State key for style check summary
        test_summary_key: State key for test analysis summary
        final_feedback_key: State key for final feedback

    Returns:
        SequentialAgent configured for the language
    """
    language_lower = language.lower()

    # OPTIMIZATION: Consolidate 4 agents → 2 agents to reduce token usage by 20-25%
    # Old pipeline: CodeAnalyzer → DesignChecker → TestAnalyzer → FeedbackSynthesizer
    # New pipeline: CodeAnalyzer (combined tools) → FeedbackReviewer (combined analysis)

    # Combined Code Analyzer Agent (structure + style checking in one agent)
    code_analyzer = Agent(
        name=f"{language}CodeAnalyzer",
        model=CODE_ANALYZER_MODEL,
        description=f"Analyzes {language} code structure, design quality, and style",
        instruction=_get_combined_analyzer_instruction(language, language_lower),
        tools=[analyzer_tool, style_tool],  # Both tools available
        output_key=structure_summary_key,
    )

    # Combined Feedback Reviewer Agent (test analysis + synthesis in one agent)
    feedback_reviewer = Agent(
        name=f"{language}FeedbackReviewer",
        model=FEEDBACK_SYNTHESIZER_MODEL,
        description=f"Analyzes test coverage and synthesizes comprehensive {language} review feedback",
        instruction=_get_combined_feedback_instruction(
            language, structure_summary_key, style_summary_key, test_summary_key
        ),
        output_key=final_feedback_key,
    )

    # Create Sequential Pipeline (2 agents instead of 4)
    return SequentialAgent(
        name=f"{language}ReviewPipeline",
        description=f"Optimized {language} code review pipeline with combined analysis and feedback",
        sub_agents=[
            code_analyzer,
            feedback_reviewer,
        ],
    )


def _get_combined_analyzer_instruction(language: str, language_lower: str) -> str:
    """Get combined instruction for code analyzer agent (structure + style).

    OPTIMIZATION: Uses STATIC_REVIEW_CONTEXT at the start for caching.
    Static content is cached, reducing token usage by 10-15%.
    """
    structure_elements = (
        "functions, classes, interfaces, imports"
        if language_lower == "typescript"
        else "functions, classes, imports"
    )

    return f"""{STATIC_REVIEW_CONTEXT}

You are a {language} code analyzer. Tasks:
1. Call analyze_{language_lower}_structure with code (pass EXACTLY as-is)
2. Call check_{language_lower}_style with "" (retrieves from state)
3. Analyze {structure_elements} per principles above

Output: {structure_elements} count, correctness/security/performance issues, design violations, style score."""


def _get_analyzer_instruction(language: str, language_lower: str) -> str:
    """DEPRECATED: Use _get_combined_analyzer_instruction instead."""
    return _get_combined_analyzer_instruction(language, language_lower)


def _get_style_checker_instruction(
    language: str, language_lower: str, style_tool: FunctionTool
) -> str:
    """Get instruction for design quality checker agent."""
    tool_name = (
        style_tool.name
        if hasattr(style_tool, "name")
        else f"check_{language_lower}_style"
    )

    return f"""You are a {language} design quality expert focused on code maintainability and architecture.

{CORE_PRINCIPLES}

{DESIGN_PRINCIPLES}

Your task:
1. Use the {tool_name} tool to validate basic style compliance
2. The tool will retrieve the ORIGINAL code from state automatically
3. Apply design principles (SOLID, DRY, YAGNI, DDD) to identify design issues
4. Report violations with evidence

CRITICAL:
- The tool checks the code EXACTLY as provided by the user
- Focus on design quality (not just formatting)
- Require concrete evidence for design violations
- Apply universal principles with {language}-specific context

Call the {tool_name} tool with an empty string for the code parameter,
as the tool will retrieve the code from state automatically.

When presenting results:
- Report the style score from the tool
- Identify design principle violations with evidence
- Show specific code examples for each issue
- Prioritize issues by actual harm (not personal preference)

Format your response as:
## Design Quality Analysis
- Style Score: [exact score]/100
- Design Issues Found: [count]

## Design Principle Violations
[List issues with evidence, file:line references]

## Recommendations
[Specific actionable fixes prioritized by impact]"""


def _get_test_analyzer_instruction(language: str, language_lower: str) -> str:
    """Get instruction for test analyzer agent."""
    test_frameworks = (
        "Jest, Vitest, Mocha, etc."
        if language_lower == "typescript"
        else "pytest, unittest, etc."
    )

    return f"""You are a testing specialist who analyzes test coverage and quality for {language} code.

{CORE_PRINCIPLES}

{TEST_PRINCIPLES}

YOUR TASK:
1. Review the code structure analysis from previous agents
2. Check if test files are provided in the review context
3. Analyze test coverage patterns ({test_frameworks})
4. Apply universal test quality principles
5. Identify missing test coverage for critical paths
6. Check for test anti-patterns (rigged tests, no assertions, over-mocking)
7. Output a detailed analysis

TESTING METHODOLOGY:
- Focus on test quality over coverage percentages
- Check if tests would actually fail if code was broken
- Verify critical paths (auth, payment, data loss) have tests
- Look for meaningful assertions (not just "is not None")
- Identify over-mocking of business logic

Output your analysis including:
- Test quality assessment (not just coverage %)
- Critical paths that need testing
- Test anti-patterns found (with examples)
- Recommendations prioritized by risk"""


def _get_combined_feedback_instruction(
    language: str,
    structure_summary_key: str,
    style_summary_key: str,
    test_summary_key: str,
) -> str:
    """Get combined instruction for feedback reviewer (test analysis + synthesis).

    OPTIMIZATION: Uses STATIC_REVIEW_CONTEXT at the start for caching.
    Static content is cached, reducing token usage by 10-15%.
    """
    return f"""{STATIC_REVIEW_CONTEXT}

You are a {language} code reviewer. Tasks:
1. Get {structure_summary_key} from state
2. Check test coverage per TEST_PRINCIPLES
3. Apply severity (HIGH/MEDIUM/LOW)
4. Synthesize per PRIORITIZATION_PRINCIPLES

Output (brief):
## Summary
One sentence. If clean: "LGTM - no significant issues."

## Correctness & Security
HIGH only (0-2 expected). If none: "LGTM"

## Design & Maintainability
MEDIUM only, top 5. If none: "LGTM"

## Test Coverage
Critical gaps only. If adequate: "LGTM"

## Issues to Address
Only if HIGH/MEDIUM exist. Skip if none.

60-80% pass rate. Be brief."""


def _get_feedback_synthesizer_instruction(
    language: str,
    structure_summary_key: str,
    style_summary_key: str,
    test_summary_key: str,
) -> str:
    """DEPRECATED: Use _get_combined_feedback_instruction instead."""
    return _get_combined_feedback_instruction(
        language, structure_summary_key, style_summary_key, test_summary_key
    )
