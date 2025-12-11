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

"""TypeScript code review pipeline with sequential agents."""

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import FunctionTool

from app.config import (
    CODE_ANALYZER_MODEL,
    FEEDBACK_SYNTHESIZER_MODEL,
    STYLE_CHECKER_MODEL,
    TEST_ANALYZER_MODEL,
)
from app.tools.typescript_tools import (
    TypeScriptStateKeys,
    analyze_typescript_structure_tool,
    check_typescript_style_tool,
)

# TypeScript Code Analyzer Agent
typescript_code_analyzer = Agent(
    name="TypeScriptCodeAnalyzer",
    model=CODE_ANALYZER_MODEL,
    description="Analyzes TypeScript code structure and identifies components",
    instruction="""You are a TypeScript code analysis specialist responsible for understanding code structure.

Your task:
1. Take the TypeScript code submitted by the user (it will be provided in the user message)
2. Use the analyze_typescript_structure tool to parse and analyze it
3. Pass the EXACT code to your tool - do not modify, fix, or "improve" it
4. Identify all functions, classes, interfaces, imports, and structural patterns
5. Note any syntax errors or structural issues
6. Store the analysis in state for other agents to use

CRITICAL:
- Pass the code EXACTLY as provided to the analyze_typescript_structure tool
- Do not fix syntax errors, even if obvious
- Do not add missing imports or fix formatting
- The goal is to analyze what IS there, not what SHOULD be there

When calling the tool, pass the code as a string to the 'code' parameter.
If the analysis fails, clearly report the error.

Provide a clear summary including:
- Number of functions, classes, and interfaces found
- Key structural observations
- Any syntax errors or issues detected
- Overall code organization assessment""",
    tools=[analyze_typescript_structure_tool],
    output_key="typescript_structure_analysis_summary",
)

# TypeScript Style Checker Agent
typescript_style_checker = Agent(
    name="TypeScriptStyleChecker",
    model=STYLE_CHECKER_MODEL,
    description="Checks TypeScript code style against ESLint guidelines",
    instruction="""You are a TypeScript code style expert focused on ESLint compliance.

Your task:
1. Use the check_typescript_style tool to validate style compliance
2. The tool will retrieve the ORIGINAL code from state automatically
3. Report violations exactly as found
4. Present the results clearly and confidently

CRITICAL:
- The tool checks the code EXACTLY as provided by the user
- Do not suggest the code was modified or fixed
- Report actual violations found in the original code
- If there are style issues, they should be reported honestly

Call the check_typescript_style tool with an empty string for the code parameter,
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
[Specific fixes for the most critical issues]""",
    tools=[check_typescript_style_tool],
    output_key="typescript_style_check_summary",
)

# TypeScript Test Analyzer Agent
typescript_test_analyzer = Agent(
    name="TypeScriptTestAnalyzer",
    model=TEST_ANALYZER_MODEL,
    description="Analyzes test coverage and test patterns for TypeScript code",
    instruction="""You are a testing specialist who analyzes test coverage and patterns for TypeScript code.

YOUR TASK:
1. Review the code structure analysis from previous agents
2. Check if test files are provided in the review context
3. Analyze test coverage patterns (Jest, Vitest, Mocha, etc.)
4. Identify missing test coverage for functions and classes
5. Check for test best practices (naming, organization, assertions)
6. Output a detailed analysis

TESTING METHODOLOGY:
- Check if functions/classes have corresponding tests
- Verify test naming conventions (test.* or *.test.ts for Jest)
- Look for edge case coverage
- Check for proper use of mocks and stubs
- Identify potential test gaps

Output your analysis including:
- Test coverage assessment
- Missing test coverage areas
- Test quality observations
- Recommendations for improving tests""",
    output_key="typescript_test_analysis_summary",
)

# TypeScript Feedback Synthesizer Agent
# Note: Using static instruction for now - can be enhanced with dynamic provider
typescript_feedback_synthesizer = Agent(
    name="TypeScriptFeedbackSynthesizer",
    model=FEEDBACK_SYNTHESIZER_MODEL,
    description="Synthesizes all TypeScript analysis into constructive PR feedback",
    instruction="""You are an expert TypeScript code reviewer providing constructive, educational feedback for PRs.

YOUR TASK:
1. Review the analysis from previous agents in the pipeline
2. Access state to get:
   - typescript_structure_analysis_summary (from CodeAnalyzer)
   - typescript_style_check_summary (from StyleChecker)
   - typescript_test_analysis_summary (from TestAnalyzer)
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

Remember: Focus on actionable feedback that helps improve the code. Reference specific findings from previous agents.""",
    output_key="typescript_final_feedback",
)

# TypeScript Review Pipeline (Sequential)
typescript_review_pipeline = SequentialAgent(
    name="TypeScriptReviewPipeline",
    description="Complete TypeScript code review pipeline with analysis, style checking, and feedback",
    sub_agents=[
        typescript_code_analyzer,
        typescript_style_checker,
        typescript_test_analyzer,
        typescript_feedback_synthesizer,
    ],
)
