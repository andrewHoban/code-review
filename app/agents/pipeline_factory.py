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
    STYLE_CHECKER_MODEL,
    TEST_ANALYZER_MODEL,
)
from app.prompts.analyzer_principles import (
    CORRECTNESS_PRINCIPLES,
    PERFORMANCE_PRINCIPLES,
    SECURITY_PRINCIPLES,
)
from app.prompts.core_principles import CORE_PRINCIPLES
from app.prompts.design_principles import DESIGN_PRINCIPLES
from app.prompts.synthesis_principles import (
    PRIORITIZATION_PRINCIPLES,
    SEVERITY_PRINCIPLES,
)
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

    # Code Analyzer Agent
    code_analyzer = Agent(
        name=f"{language}CodeAnalyzer",
        model=CODE_ANALYZER_MODEL,
        description=f"Analyzes {language} code structure and identifies components",
        instruction=_get_analyzer_instruction(language, language_lower),
        tools=[analyzer_tool],
        output_key=structure_summary_key,
    )

    # Design Quality Checker Agent (formerly StyleChecker)
    design_checker = Agent(
        name=f"{language}DesignChecker",
        model=STYLE_CHECKER_MODEL,
        description=f"Checks {language} code design quality (SOLID, DRY, YAGNI, DDD) and style",
        instruction=_get_style_checker_instruction(
            language, language_lower, style_tool
        ),
        tools=[style_tool],
        output_key=style_summary_key,
    )

    # Test Analyzer Agent
    test_analyzer = Agent(
        name=f"{language}TestAnalyzer",
        model=TEST_ANALYZER_MODEL,
        description=f"Analyzes test coverage and test patterns for {language} code",
        instruction=_get_test_analyzer_instruction(language, language_lower),
        output_key=test_summary_key,
    )

    # Feedback Synthesizer Agent
    feedback_synthesizer = Agent(
        name=f"{language}FeedbackSynthesizer",
        model=FEEDBACK_SYNTHESIZER_MODEL,
        description=f"Synthesizes all {language} analysis into constructive PR feedback",
        instruction=_get_feedback_synthesizer_instruction(
            language, structure_summary_key, style_summary_key, test_summary_key
        ),
        output_key=final_feedback_key,
    )

    # Create Sequential Pipeline
    return SequentialAgent(
        name=f"{language}ReviewPipeline",
        description=f"Complete {language} code review pipeline with analysis, design checking, and feedback",
        sub_agents=[
            code_analyzer,
            design_checker,
            test_analyzer,
            feedback_synthesizer,
        ],
    )


def _get_analyzer_instruction(language: str, language_lower: str) -> str:
    """Get instruction for code analyzer agent."""
    structure_elements = (
        "functions, classes, interfaces, imports, and structural patterns"
        if language_lower == "typescript"
        else "functions, classes, imports, and structural patterns"
    )

    return f"""You are a {language} code analysis specialist responsible for understanding code structure and identifying issues.

{CORE_PRINCIPLES}

{CORRECTNESS_PRINCIPLES}

{SECURITY_PRINCIPLES}

{PERFORMANCE_PRINCIPLES}

Your task:
1. Take the {language} code submitted by the user (it will be provided in the user message)
2. Use the analyze_{language_lower}_structure tool to parse and analyze it
3. Pass the EXACT code to your tool - do not modify, fix, or "improve" it
4. Identify all {structure_elements}
5. Apply the above principles to find correctness, security, and performance issues
6. Store the analysis in state for other agents to use

CRITICAL:
- Pass the code EXACTLY as provided to the analyze_{language_lower}_structure tool
- Do not fix syntax errors, even if obvious
- Do not add missing imports or fix formatting
- The goal is to analyze what IS there, not what SHOULD be there
- Apply universal principles with {language}-specific adaptations

When calling the tool, pass the code as a string to the 'code' parameter.
If the analysis fails, clearly report the error.

Provide a clear summary including:
- Number of {structure_elements.replace(" and ", ", ")}
- Key structural observations
- Correctness, security, and performance issues found
- Overall code organization assessment"""


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


def _get_feedback_synthesizer_instruction(
    language: str,
    structure_summary_key: str,
    style_summary_key: str,
    test_summary_key: str,
) -> str:
    """Get instruction for feedback synthesizer agent."""
    return f"""You are an expert {language} code reviewer providing constructive, educational feedback for PRs.

{CORE_PRINCIPLES}

{SEVERITY_PRINCIPLES}

{PRIORITIZATION_PRINCIPLES}

YOUR TASK:
1. Review the analysis from previous agents in the pipeline
2. Access state to get:
   - {structure_summary_key} (from CodeAnalyzer)
   - {style_summary_key} (from DesignChecker)
   - {test_summary_key} (from TestAnalyzer)
3. Apply severity levels to all findings
4. Prioritize issues (security first, then correctness, then everything else)
5. Synthesize into comprehensive feedback
6. Generate inline comments for HIGH issues (with file path and line numbers)
7. Provide actionable recommendations

FEEDBACK STRUCTURE TO FOLLOW:

## 📊 Summary
Provide an honest assessment. Remember expected pass rate is 60-80%.
Be encouraging but truthful about problems found.

## ✅ Strengths
List 2-3 things done well, referencing specific code elements.

## 📈 Code Quality Analysis

### Correctness & Security (HIGH priority findings)
List HIGH severity issues (expect 0-2 per review):
- Security vulnerabilities with demonstrated exploits
- Data loss/corruption scenarios
- Crash/outage paths

### Design & Maintainability (MEDIUM priority findings)
List top 5 MEDIUM severity issues by impact

### Test Coverage & Quality (focus on critical paths)
Report critical paths that need testing, test anti-patterns found

## 💡 Recommendations for Improvement
Prioritized list:
1. Security issues (any severity)
2. HIGH severity correctness issues
3. Top 5 MEDIUM issues by impact
4. Top 3 LOW quick wins (<5 min to fix)

## 🎯 Next Steps
Based on severity, what MUST be fixed vs what SHOULD be improved.

Remember: Focus on real issues that cause actual harm. Pass rate should be 60-80%."""
