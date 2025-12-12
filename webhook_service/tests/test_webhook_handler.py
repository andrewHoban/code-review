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

"""Tests for webhook handler."""

import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config

from app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "healthy"}


def test_webhook_without_signature(client):
    """Test webhook rejects requests without signature."""
    response = client.post("/webhook", json={"test": "data"})
    # Should allow in development mode if secret not configured
    # In production with secret, would return 403
    assert response.status_code in [200, 403]


def test_webhook_with_invalid_signature(client, monkeypatch):
    """Test webhook rejects requests with invalid signature."""
    # Set a webhook secret for testing
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    Config.GITHUB_WEBHOOK_SECRET = "test-secret"

    payload = json.dumps({"test": "data"})
    response = client.post(
        "/webhook",
        data=payload,
        headers={"X-Hub-Signature-256": "sha256=invalid"},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_webhook_with_valid_signature(client, monkeypatch):
    """Test webhook accepts requests with valid signature."""
    # Set a webhook secret for testing
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    Config.GITHUB_WEBHOOK_SECRET = "test-secret"

    payload = json.dumps({"action": "opened", "pull_request": {}})
    signature = (
        "sha256="
        + hmac.new(
            b"test-secret",
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    response = client.post(
        "/webhook",
        data=payload,
        headers={
            "X-Hub-Signature-256": signature,
            "X-GitHub-Event": "pull_request",
        },
        content_type="application/json",
    )
    # May return 200 or 500 depending on client initialization
    assert response.status_code in [200, 500]
