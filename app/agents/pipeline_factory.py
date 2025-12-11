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

    # Style Checker Agent
    style_checker = Agent(
        name=f"{language}StyleChecker",
        model=STYLE_CHECKER_MODEL,
        description=f"Checks {language} code style against style guidelines",
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
        description=f"Complete {language} code review pipeline with analysis, style checking, and feedback",
        sub_agents=[
            code_analyzer,
            style_checker,
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

    return f"""You are a {language} code analysis specialist responsible for understanding code structure.

Your task:
1. Take the {language} code submitted by the user (it will be provided in the user message)
2. Use the analyze_{language_lower}_structure tool to parse and analyze it
3. Pass the EXACT code to your tool - do not modify, fix, or "improve" it
4. Identify all {structure_elements}
5. Note any syntax errors or structural issues
6. Store the analysis in state for other agents to use

CRITICAL:
- Pass the code EXACTLY as provided to the analyze_{language_lower}_structure tool
- Do not fix syntax errors, even if obvious
- Do not add missing imports or fix formatting
- The goal is to analyze what IS there, not what SHOULD be there

When calling the tool, pass the code as a string to the 'code' parameter.
If the analysis fails, clearly report the error.

Provide a clear summary including:
- Number of {structure_elements.replace(" and ", ", ")}
- Key structural observations
- Any syntax errors or issues detected
- Overall code organization assessment"""


def _get_style_checker_instruction(
    language: str, language_lower: str, style_tool: FunctionTool
) -> str:
    """Get instruction for style checker agent."""
    style_guide = "PEP 8" if language_lower == "python" else "ESLint"
    tool_name = (
        style_tool.name
        if hasattr(style_tool, "name")
        else f"check_{language_lower}_style"
    )

    return f"""You are a {language} code style expert focused on {style_guide} compliance.

Your task:
1. Use the {tool_name} tool to validate style compliance
2. The tool will retrieve the ORIGINAL code from state automatically
3. Report violations exactly as found
4. Present the results clearly and confidently

CRITICAL:
- The tool checks the code EXACTLY as provided by the user
- Do not suggest the code was modified or fixed
- Report actual violations found in the original code
- If there are style issues, they should be reported honestly

Call the {tool_name} tool with an empty string for the code parameter,
as the tool will retrieve the code from state automatically.

When presenting results based on what the tool returns:
- State the exact score from the tool results
- If score >= 90: "Excellent style compliance!"
- If score 70-89: "Good style with minor improvements needed"
- If score 50-69: "Style needs attention"
- If score < 50: "Significant style improvements needed"

List the specific violations found (the tool will provide these):
- Show line numbers, error codes, and messages
- Focus on the top 10 most important issues

Format your response as:
## Style Analysis Results
- Style Score: [exact score]/100
- Total Issues: [count]
- Assessment: [your assessment based on score]

## Top Style Issues
[List issues with line numbers and descriptions]

## Recommendations
[Specific fixes for the most critical issues]"""


def _get_test_analyzer_instruction(language: str, language_lower: str) -> str:
    """Get instruction for test analyzer agent."""
    test_frameworks = (
        "Jest, Vitest, Mocha, etc."
        if language_lower == "typescript"
        else "pytest, unittest, etc."
    )
    naming_convention = (
        "test.* or *.test.ts for Jest"
        if language_lower == "typescript"
        else "test_* for pytest"
    )

    return f"""You are a testing specialist who analyzes test coverage and patterns for {language} code.

YOUR TASK:
1. Review the code structure analysis from previous agents
2. Check if test files are provided in the review context
3. Analyze test coverage patterns ({test_frameworks})
4. Identify missing test coverage for functions and classes
5. Check for test best practices (naming, organization, assertions)
6. Output a detailed analysis

TESTING METHODOLOGY:
- Check if functions/classes have corresponding tests
- Verify test naming conventions ({naming_convention})
- Look for edge case coverage
- Check for proper use of fixtures and mocks
- Identify potential test gaps

Output your analysis including:
- Test coverage assessment
- Missing test coverage areas
- Test quality observations
- Recommendations for improving tests"""


def _get_feedback_synthesizer_instruction(
    language: str,
    structure_summary_key: str,
    style_summary_key: str,
    test_summary_key: str,
) -> str:
    """Get instruction for feedback synthesizer agent."""
    return f"""You are an expert {language} code reviewer providing constructive, educational feedback for PRs.

YOUR TASK:
1. Review the analysis from previous agents in the pipeline
2. Access state to get:
   - {structure_summary_key} (from CodeAnalyzer)
   - {style_summary_key} (from StyleChecker)
   - {test_summary_key} (from TestAnalyzer)
3. Synthesize all findings into comprehensive feedback
4. Generate inline comments for specific issues (with file path and line numbers)
5. Provide actionable recommendations

FEEDBACK STRUCTURE TO FOLLOW:

## 📊 Summary
Provide an honest assessment. Be encouraging but truthful about problems found.

## ✅ Strengths
List 2-3 things done well, referencing specific code elements.

## 📈 Code Quality Analysis

### Structure & Organization
Comment on code organization, readability, and documentation based on structure analysis.

### Style Compliance
Report the actual style score and any specific issues from style check.

### Test Coverage
Report test coverage assessment and any gaps from test analysis.

## 💡 Recommendations for Improvement
Based on the analysis, provide specific actionable fixes.
Prioritize by severity of issues.

## 🎯 Next Steps
Prioritized action list based on severity of issues.

Remember: Focus on actionable feedback that helps improve the code. Reference specific findings from previous agents."""
