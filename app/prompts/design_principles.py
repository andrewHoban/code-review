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

"""Design principles - SOLID, DRY, YAGNI, DDD, and readability."""

DESIGN_PRINCIPLES = """
DESIGN QUALITY (Medium Priority):

1. Single Responsibility Principle:
   - Flag if: Function/class does multiple unrelated things
   - Evidence: "This function both validates input AND saves to database AND sends email"
   - Fix: Split into separate functions with clear names
   - Skip: Subjective "could be cleaner" without clear harm

2. DRY (Don't Repeat Yourself):
   - Flag if: Identical logic duplicated 3+ times
   - Evidence: Show the duplicated code blocks
   - Fix: Extract to shared function/constant
   - Skip: Similar-looking code that has different purposes
   - Skip: Duplication <3 times (might not be pattern yet)

3. YAGNI (You Aren't Gonna Need It):
   - Flag if: Unused code, parameters, or abstractions
   - Evidence: "This parameter is never used", "This class has no callers"
   - Flag if: Overly generic code without current use cases
   - Evidence: "This supports 5 formats but only 1 is used"
   - Skip: Reasonable extension points with 2+ current uses

4. Domain-Driven Design (Strategic):
   - Flag if: Business logic mixed with infrastructure (DB, HTTP, UI)
   - Evidence: "Controller contains pricing calculation logic"
   - Flag if: Inconsistent terminology for same concept
   - Evidence: "Called 'User' here but 'Account' there"
   - Flag if: Domain boundaries unclear (one module does everything)
   - Skip: Tactical DDD patterns (Entities, Value Objects, Aggregates)

5. Readability:
   - Functions >80 lines (hard to understand)
   - Nesting >4 levels (cognitive overload)
   - Meaningless names (x, data, info, temp, manager)
   - Magic numbers (except 0, 1, -1, true, false, empty string)

Skip Always:
- Formatting/whitespace (tools handle this)
- Personal preferences (tabs vs spaces, braces style)
- Abstract "could be better" without demonstrable harm
"""
