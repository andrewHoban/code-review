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

"""Configuration management for webhook service."""

import os

from google.cloud import secretmanager


class Config:
    """Configuration for webhook service."""

    # GitHub App configuration
    GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
    GITHUB_APP_PRIVATE_KEY = None  # Will be loaded from Secret Manager
    GITHUB_WEBHOOK_SECRET = None  # Will be loaded from Secret Manager

    # GCP configuration
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "bpc-askgreg-nonprod")
    GCP_REGION = os.getenv("GCP_REGION", "europe-west1")
    AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID", "3659508948773371904")

    # Secret Manager paths
    @classmethod
    def _get_secret_path(cls, secret_name: str) -> str:
        """Get full secret path for Secret Manager."""
        return f"projects/{cls.GCP_PROJECT_ID}/secrets/{secret_name}/versions/latest"

    PRIVATE_KEY_SECRET = None  # Will be set dynamically
    WEBHOOK_SECRET_SECRET = None  # Will be set dynamically

    @classmethod
    def load_secrets(cls):
        """Load secrets from Google Secret Manager or environment variables."""
        # For local development, allow loading from env vars
        if os.getenv("GITHUB_WEBHOOK_SECRET"):
            cls.GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
        else:
            # Try to load from Secret Manager
            try:
                client = secretmanager.SecretManagerServiceClient()
                cls.PRIVATE_KEY_SECRET = cls._get_secret_path("github-app-private-key")
                cls.WEBHOOK_SECRET_SECRET = cls._get_secret_path(
                    "github-webhook-secret"
                )

                # Load private key
                try:
                    private_key_response = client.access_secret_version(
                        name=cls.PRIVATE_KEY_SECRET
                    )
                    cls.GITHUB_APP_PRIVATE_KEY = (
                        private_key_response.payload.data.decode("UTF-8")
                    )
                except Exception as e:
                    # If secret doesn't exist, try env var
                    if os.getenv("GITHUB_APP_PRIVATE_KEY"):
                        cls.GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY")
                    else:
                        raise Exception(
                            f"Could not load GitHub App private key: {e}"
                        ) from e

                # Load webhook secret
                try:
                    webhook_secret_response = client.access_secret_version(
                        name=cls.WEBHOOK_SECRET_SECRET
                    )
                    cls.GITHUB_WEBHOOK_SECRET = (
                        webhook_secret_response.payload.data.decode("UTF-8")
                    )
                except Exception as e:
                    # If secret doesn't exist, try env var
                    if os.getenv("GITHUB_WEBHOOK_SECRET"):
                        cls.GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
                    else:
                        raise Exception(f"Could not load webhook secret: {e}") from e
            except Exception as e:
                # Fallback to environment variables for local development
                if os.getenv("GITHUB_APP_PRIVATE_KEY"):
                    cls.GITHUB_APP_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY")
                if os.getenv("GITHUB_WEBHOOK_SECRET"):
                    cls.GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
                if not cls.GITHUB_WEBHOOK_SECRET:
                    # Only warn in production, allow None for local dev
                    print(f"Warning: Could not load secrets: {e}")
