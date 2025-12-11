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

"""Core review principles - universal across all languages and agents."""

CORE_PRINCIPLES = """
REVIEW PRINCIPLES:

1. Real Issues Only:
   - Flag only if: correctness bug, security risk, or performance problem
   - NOT style preferences, personal taste, or "could be better"
   - Ask: "What actual harm does this cause?"

2. Expected Pass Rate: 60-80%
   - Most code is acceptable with minor improvements
   - High severity issues are rare (0-2 per review)
   - Pass more often than fail

3. Be Specific:
   - Reference exact file:line
   - Show code snippet
   - Explain concrete harm, not vague concerns

4. When Uncertain (confidence <70%):
   - Say so explicitly
   - Explain what's unclear
   - Suggest alternatives, don't demand changes

5. Tone & Brevity:
   - Engineers value conciseness over encouragement
   - Use "LGTM" (looks good to me) when sections have no issues
   - Skip praise, congratulations, and "what went well" sections
   - If everything is fine, say "LGTM" and nothing more
   - Focus exclusively on issues that need addressing
"""
