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

"""Configuration for code review agent models and settings."""

import os

# Model configuration
# Note: gemini-3-pro-preview is not available in europe-west1
# Using gemini-2.5-pro for the single-agent architecture

# Primary model with fallback for reliability
# The fallback model will be used automatically when the primary model encounters
# errors (quota limits, model unavailable, etc.) via the ModelFallbackAgent.
LANGUAGE_DETECTOR_MODEL = os.getenv("LANGUAGE_DETECTOR_MODEL", "gemini-2.5-pro")
LANGUAGE_DETECTOR_FALLBACK_MODEL = os.getenv(
    "LANGUAGE_DETECTOR_FALLBACK_MODEL", "gemini-2.5-flash"
)

# Review configuration
MAX_INLINE_COMMENTS = int(os.getenv("MAX_INLINE_COMMENTS", "50"))
REVIEW_TIMEOUT_SECONDS = int(os.getenv("REVIEW_TIMEOUT_SECONDS", "300"))

# Note: Style checking configuration removed - the simplified agent uses
# LLM reasoning instead of structured style checking tools
