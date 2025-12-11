# ==============================================================================
# Installation & Setup
# ==============================================================================

# Install dependencies using uv package manager
install:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/0.8.13/install.sh | sh; source $HOME/.local/bin/env; }
	uv sync

# ==============================================================================
# Playground Targets
# ==============================================================================

# Launch local dev playground
playground:
	@echo "==============================================================================="
	@echo "| 🚀 Starting your agent playground...                                        |"
	@echo "|                                                                             |"
	@echo "| 💡 Try asking: What's the weather in San Francisco?                         |"
	@echo "|                                                                             |"
	@echo "| 🔍 IMPORTANT: Select the 'app' folder to interact with your agent.          |"
	@echo "==============================================================================="
	uv run adk web . --port 8501 --reload_agents

# ==============================================================================
# Backend Deployment Targets
# ==============================================================================

# Validate before deployment (catches common issues early)
test-deploy:
	@echo "🔍 Validating deployment readiness..."
	@echo "1. Testing Python syntax..."
	@uv run python -m py_compile app/agent_engine_app.py app/agent.py
	@echo "2. Testing imports..."
	@uv run python -c "from app.agent_engine_app import agent_engine; print('✓ Imports successful')"
	@echo "3. Checking requirements generation..."
	@uv export --no-hashes --no-header --no-dev --no-emit-project 2>/dev/null | sed '/^[[:space:]]*#/d' | sed '/^[[:space:]]*$$/d' | sed '/^Resolved/d' > app/app_utils/.requirements.txt.test
	@if ! grep -q "google-cloud-aiplatform" app/app_utils/.requirements.txt.test; then echo "❌ ERROR: google-cloud-aiplatform missing from requirements"; rm app/app_utils/.requirements.txt.test; exit 1; fi
	@echo "✓ google-cloud-aiplatform found in requirements"
	@rm app/app_utils/.requirements.txt.test
	@echo "✅ All pre-deployment checks passed!"

# Deploy the agent remotely
deploy:
	# Export dependencies to requirements file using uv export.
	uv export --no-hashes --no-header --no-dev --no-emit-project 2>/dev/null | sed '/^[[:space:]]*#/d' | sed '/^[[:space:]]*$$/d' | sed '/^Resolved/d' > app/app_utils/.requirements.txt && \
	uv run -m app.app_utils.deploy \
		--source-packages=./app \
		--entrypoint-module=app.agent_engine_app \
		--entrypoint-object=agent_engine \
		--requirements-file=app/app_utils/.requirements.txt \
		--location=europe-west1

# Alias for 'make deploy' for backward compatibility
backend: deploy

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

# Run unit and integration tests (fast, excludes E2E)
test:
	uv sync --dev
	uv run pytest tests/unit tests/integration -m "not e2e"

# Run all tests including E2E (slow - real API calls)
test-all:
	uv sync --dev
	uv run pytest tests/unit tests/integration tests/e2e

# Run code quality checks (codespell, ruff, mypy)
lint:
	uv sync --dev --extra lint
	uv run codespell
	uv run ruff check . --diff
	uv run ruff format . --check --diff
	uv run mypy .

# ==============================================================================
# Gemini Enterprise Integration
# ==============================================================================

# Register the deployed agent to Gemini Enterprise
# Usage: make register-gemini-enterprise (interactive - will prompt for required details)
# For non-interactive use, set env vars: ID or GEMINI_ENTERPRISE_APP_ID (full GE resource name)
# Optional env vars: GEMINI_DISPLAY_NAME, GEMINI_DESCRIPTION, GEMINI_TOOL_DESCRIPTION, AGENT_ENGINE_ID
register-gemini-enterprise:
	@uvx agent-starter-pack@0.27.0 register-gemini-enterprise
