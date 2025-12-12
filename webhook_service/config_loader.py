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

"""Load repository-specific configuration from .code-review.yml."""

import logging

import yaml
from github_client import GitHubClient

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "enabled": True,
    "languages": ["python", "typescript"],
    "rules": {
        "max_line_length": 100,
        "style_check": True,
        "require_tests": True,
    },
    "ignore_paths": [],
    "severity_threshold": "info",
}


class ConfigLoader:
    """Load per-repository configuration from .code-review.yml."""

    def __init__(self, github_client: GitHubClient):
        """Initialize config loader.

        Args:
            github_client: GitHub client instance
        """
        self.github_client = github_client

    def load_repo_config(
        self,
        installation_id: int,
        repo_full_name: str,
        branch: str = "main",
    ) -> dict:
        """Load configuration from repository's .code-review.yml file.

        If file doesn't exist, returns default configuration.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository full name
            branch: Branch to read config from

        Returns:
            Configuration dictionary
        """
        try:
            content = self.github_client.get_file_content(
                installation_id, repo_full_name, ".code-review.yml", ref=branch
            )

            if not content:
                return DEFAULT_CONFIG

            # Parse YAML
            config = yaml.safe_load(content)

            # Merge with defaults
            merged_config = {**DEFAULT_CONFIG, **config.get("code_review", {})}
            logger.info(f"Loaded config from .code-review.yml for {repo_full_name}")
            return merged_config

        except Exception as e:
            # If file doesn't exist or any error, return defaults
            logger.debug(f"Could not load .code-review.yml for {repo_full_name}: {e}")
            return DEFAULT_CONFIG
