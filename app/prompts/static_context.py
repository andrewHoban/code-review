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

"""Static review principles for context caching.

This module contains all review principles that remain constant across reviews.
These principles are designed to be cached by Gemini's context caching feature,
reducing token usage by 10-15% when cached.

Structure prompts to put this content FIRST (before dynamic PR-specific data)
so it can be cached and reused across multiple requests.
"""

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

# Combined static context for caching
# This should be placed at the START of agent instructions to enable caching
STATIC_REVIEW_CONTEXT = f"""
{CORE_PRINCIPLES}

{CORRECTNESS_PRINCIPLES}

{SECURITY_PRINCIPLES}

{PERFORMANCE_PRINCIPLES}

{DESIGN_PRINCIPLES}

{TEST_PRINCIPLES}

{SEVERITY_PRINCIPLES}

{PRIORITIZATION_PRINCIPLES}
"""
