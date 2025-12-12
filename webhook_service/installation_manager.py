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

"""Installation management for tracking GitHub App installations."""

import logging
from datetime import datetime

from config import Config
from google.cloud import firestore

logger = logging.getLogger(__name__)


class InstallationManager:
    """Manage GitHub App installation tracking in Firestore."""

    def __init__(self):
        """Initialize installation manager."""
        try:
            self.db = firestore.Client(project=Config.GCP_PROJECT_ID)
            self.installations_collection = self.db.collection("installations")
            logger.info("Firestore client initialized")
        except Exception as e:
            logger.warning(
                f"Could not initialize Firestore: {e}. Installation tracking disabled."
            )
            self.db = None
            self.installations_collection = None

    def add_installation(self, installation_id: int, repositories: list[str]):
        """Record a new installation.

        Args:
            installation_id: GitHub App installation ID
            repositories: List of repository full names
        """
        if not self.installations_collection:
            logger.warning("Firestore not available, skipping installation tracking")
            return

        try:
            doc_ref = self.installations_collection.document(str(installation_id))
            doc_ref.set(
                {
                    "installation_id": installation_id,
                    "repositories": repositories,
                    "installed_at": datetime.utcnow(),
                    "active": True,
                }
            )
            logger.info(
                f"Recorded installation {installation_id} with {len(repositories)} repositories"
            )
        except Exception as e:
            logger.error(f"Error recording installation: {e}")

    def remove_installation(self, installation_id: int):
        """Mark an installation as inactive.

        Args:
            installation_id: GitHub App installation ID
        """
        if not self.installations_collection:
            return

        try:
            doc_ref = self.installations_collection.document(str(installation_id))
            doc_ref.update({"active": False, "uninstalled_at": datetime.utcnow()})
            logger.info(f"Marked installation {installation_id} as inactive")
        except Exception as e:
            logger.error(f"Error removing installation: {e}")

    def update_installation_repositories(
        self, installation_id: int, repositories: list[str]
    ):
        """Update repositories for an installation.

        Args:
            installation_id: GitHub App installation ID
            repositories: List of repository full names
        """
        if not self.installations_collection:
            return

        try:
            doc_ref = self.installations_collection.document(str(installation_id))
            doc_ref.update({"repositories": repositories})
            logger.info(
                f"Updated installation {installation_id} with {len(repositories)} repositories"
            )
        except Exception as e:
            logger.error(f"Error updating installation: {e}")

    def get_installation(self, installation_id: int) -> dict | None:
        """Get installation details.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            Installation document as dictionary, or None if not found
        """
        if not self.installations_collection:
            return None

        try:
            doc_ref = self.installations_collection.document(str(installation_id))
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error getting installation: {e}")
            return None

    def is_repository_enabled(self, installation_id: int, repo_full_name: str) -> bool:
        """Check if a repository has the app enabled.

        Args:
            installation_id: GitHub App installation ID
            repo_full_name: Repository full name

        Returns:
            True if repository is enabled, False otherwise
        """
        installation = self.get_installation(installation_id)
        if not installation or not installation.get("active"):
            return False

        repositories = installation.get("repositories", [])
        return repo_full_name in repositories
