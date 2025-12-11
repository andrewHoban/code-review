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

"""Synthesis principles - severity levels and prioritization."""

SEVERITY_PRINCIPLES = """
SEVERITY LEVELS:

HIGH (Must Fix):
- Security vulnerability with demonstrated exploit
- Data loss/corruption scenario
- Crash/outage path
- Correctness bug in critical path (auth, payment, data integrity)

MEDIUM (Should Fix):
- Security issue without clear exploit path
- Performance degradation (measurable)
- Missing error handling (non-critical paths)
- Resource leak (minor)
- Inconsistent error handling

LOW (Optional):
- Readability issues (long functions, complex code)
- Missing tests (non-critical paths)
- Minor inconsistencies
- Maintainability concerns

Rule: High findings are rare (0-2 per review). Most reviews have 0-3 Medium, 2-5 Low.
"""

PRIORITIZATION_PRINCIPLES = """
PRIORITIZATION:

1. Security first (any severity)
2. Correctness in critical paths (High)
3. Everything else by severity

Limit output:
- High: Show all (expect 0-2)
- Medium: Top 5 by impact
- Low: Top 3 quick wins (<5 min to fix)

Skip:
- Listing same issue across many files (show one example + count)
- Nitpicking every minor style issue
- Suggesting rewrites without clear benefit
"""
