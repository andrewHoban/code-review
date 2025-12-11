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

"""Test quality principles - universal testing best practices."""

TEST_PRINCIPLES = """
TEST QUALITY:

Red Flags (High Priority):
1. Rigged tests: Assertions so weak they always pass
   Bad: assert result is not None
   Good: assert result == expected_value

2. No assertions: Test runs code but doesn't verify behavior
   Bad: process_data(input)  # No assert
   Good: assert process_data(input).status == "success"

3. Over-mocked: Mocking business logic (not just external I/O)
   Bad: Mock every function call
   Good: Mock only API/DB/filesystem

4. Testing framework code instead of your code

Coverage Expectations:
- Critical paths (auth, payment, data loss scenarios): Must be tested
- Business logic: Should be tested
- Utilities/config: Optional

Don't Require:
- 100% coverage (80% is often sufficient)
- Tests for trivial getters/setters
- Tests for every edge case (focus on likely scenarios)

Measure: Would this test fail if the code was broken?
"""
