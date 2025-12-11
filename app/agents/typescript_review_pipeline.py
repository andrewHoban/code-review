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

from app.agents.pipeline_factory import create_review_pipeline
from app.tools.typescript_tools import (
    analyze_typescript_structure_tool,
    check_typescript_style_tool,
)

# TypeScript Review Pipeline (Sequential)
typescript_review_pipeline = create_review_pipeline(
    language="TypeScript",
    analyzer_tool=analyze_typescript_structure_tool,
    style_tool=check_typescript_style_tool,
    structure_summary_key="typescript_structure_analysis_summary",
    style_summary_key="typescript_style_check_summary",
    test_summary_key="typescript_test_analysis_summary",
    final_feedback_key="typescript_final_feedback",
)
