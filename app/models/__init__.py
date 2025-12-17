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

"""Data models for code review agent input and output schemas."""

from app.models.input_schema import (
    ChangedFile,
    CodeReviewInput,
    FileDependencies,
    PullRequestMetadata,
    RelatedFile,
    RepositoryInfo,
    ReviewContext,
    TestFile,
)
from app.models.output_schema import (
    CodeReviewOutput,
    InlineComment,
    ReviewMetrics,
    SimpleReviewOutput,
)

__all__ = [
    "ChangedFile",
    "CodeReviewInput",
    "CodeReviewOutput",
    "FileDependencies",
    "InlineComment",
    "PullRequestMetadata",
    "RelatedFile",
    "RepositoryInfo",
    "ReviewContext",
    "ReviewMetrics",
    "SimpleReviewOutput",
    "TestFile",
]
