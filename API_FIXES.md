# Agent Engine API Implementation Fixes

## Summary of Issues

The implementation had several issues related to incorrect usage of the Vertex AI Agent Engine API. This document outlines all problems found and the fixes applied.

## Issues Identified

### 1. Incorrect API Initialization
**Problem:** Using `agent_engines.get()` directly instead of through the client
**Location:** `scripts/call_agent.py`

**Before:**
```python
from vertexai import agent_engines
vertexai.init(project=project_id, location=location)
agent = agent_engines.get(resource_name=resource_name)
```

**After:**
```python
import vertexai
client = vertexai.Client(project=project_id, location=location)
agent = client.agent_engines.get(name=resource_name)
```

**Reason:** The modern Vertex AI SDK (v1.112.0+) uses a client-based design where `agent_engines` is accessed through `vertexai.Client().agent_engines`.

### 2. Incorrect Parameter Name for get()
**Problem:** Using `resource_name` instead of `name`
**Location:** `scripts/call_agent.py`

**Before:**
```python
agent = agent_engines.get(resource_name=resource_name)
```

**After:**
```python
agent = client.agent_engines.get(name=resource_name)
```

**Reason:** The `get()` method expects a parameter named `name`, not `resource_name`.

### 3. Incorrect query() Method Parameters
**Problem:** Using wrong parameter names (`message` and `user_id`) instead of `input`
**Location:** `scripts/call_agent.py`

**Before:**
```python
response = agent.query(message=json.dumps(payload), user_id=user_id)
```

**After:**
```python
response = agent.query(input=json.dumps(payload))
```

**Reason:** The agent's `query()` method expects an `input` parameter. The `user_id` is handled internally by the Agent Engine based on the session context.

### 4. Incorrect Session Management
**Problem:** Attempting to create a session and call `session.query()`
**Location:** `scripts/call_agent.py` (previous iteration)

**Before:**
```python
session = agent.create_session(user_id=user_id)
response = session.query(input=json.dumps(payload))
```

**After:**
```python
response = agent.query(input=json.dumps(payload))
```

**Reason:** For Agent Engine deployments, you query the agent directly, not through a separate session object. The Agent Engine manages sessions internally.

## Updated Documentation

### Correct API Usage Pattern

```python
import json
import vertexai

# Initialize client
client = vertexai.Client(
    project="YOUR_PROJECT_ID",
    location="YOUR_LOCATION"
)

# Get deployed agent
agent = client.agent_engines.get(
    name="projects/PROJECT_ID/locations/LOCATION/reasoningEngines/RESOURCE_ID"
)

# Query the agent
response = agent.query(input=json.dumps(payload))

# Parse response
if isinstance(response, str):
    result = json.loads(response)
elif hasattr(response, "text"):
    result = json.loads(response.text)
else:
    result = json.loads(str(response))
```

## API Confusion Sources

The confusion arose from multiple API patterns in documentation:

1. **Old API (vertexai.preview.reasoning_engines):**
   - Used for custom reasoning engines
   - Has different calling patterns
   - Still in preview

2. **New API (vertexai.Client().agent_engines):**
   - Current recommended approach
   - Client-based design (v1.112.0+)
   - Used for ADK agents deployed to Agent Engine

3. **Mixed Documentation:**
   - Some documentation shows `agent_engines` module directly
   - Some shows it through `vertexai.Client()`
   - Parameter names vary in examples (`message` vs `input`, `user_id` placement)

## Files Fixed

1. **scripts/call_agent.py**
   - Fixed API initialization
   - Fixed get() parameter name
   - Fixed query() parameters
   - Removed unused import

2. **DEPLOYMENT_INFO.md**
   - Updated code examples to use correct API
   - Fixed import statements
   - Corrected query() method parameters

## Testing Recommendations

1. Test the updated `call_agent.py` locally:
```bash
python scripts/call_agent.py \
  --payload=tests/fixtures/python_simple_pr.json \
  --output=test_response.json \
  --project-id=bpc-askgreg-nonprod \
  --location=europe-west1 \
  --agent-engine-id=3659508948773371904
```

2. Verify the GitHub Actions workflow runs successfully

3. Check the Cloud Console playground to ensure the agent is responsive

## References

- [Vertex AI Agent Engine Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/manage/overview)
- [Agent Engine Migration Guide](https://cloud.google.com/vertex-ai/generative-ai/docs/deprecations/agent-engine-migration)
- [Vertex AI Python SDK Reference](https://cloud.google.com/python/docs/reference/vertexai/latest/vertexai.agent_engines)
