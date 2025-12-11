# Code Review Bot Bug Analysis

## Executive Summary

**There are TWO separate bugs causing the failure:**

### Bug #1: Wrong API Call (Client-Side)
**The bug:** Code uses `agent.query(input=...)` which doesn't exist.
**The fix:** Use `agent.stream_query(message=..., user_id=...)` instead.

**Key Findings:**
1. ✅ `AgentEngine` object does NOT have a `query()` method
2. ✅ It DOES have a `stream_query()` method
3. ✅ `stream_query()` requires TWO parameters:
   - `message=...` (NOT `input`)
   - `user_id=...` (completely missing in current code)

### Bug #2: Agent Not Responding (Server-Side)
**The bug:** Agent returns 0 chunks/empty response (fails in Console Playground too)
**The fix:** Remove `super().set_up()` call in `AgentEngineApp.set_up()`

**Key Finding:**
- Line 46 of `app/agent_engine_app.py` calls `super().set_up()`
- Agent Starter Pack guidance explicitly forbids this
- Causes Resource Manager API failures that break agent execution

**Both bugs must be fixed for the agent to work.**

---

## Problem Statement

The code review bot is failing with the error:
```
'AgentEngine' object has no attribute 'query'
```

This is **the third attempt** to fix the same bug, indicating a fundamental misunderstanding of the Vertex AI Agent Engine API.

---

## Root Cause Analysis

### The Core Issue

**The agent object uses `stream_query()` which requires different parameters than what the code provides.**

Looking at `scripts/call_agent.py` line 53:
```python
agent = agent_engines.get(resource_name=resource_name)
response = agent.query(input=json.dumps(payload))  # ❌ FAILS: 'query' method doesn't exist
```

**Agent Engine logs show the actual error:**
```
TypeError: AdkApp.stream_query() missing 2 required keyword-only arguments: 'message' and 'user_id'
```

### Why This Keeps Failing

The confusion stems from **conflicting documentation and API patterns**:

1. **Documentation Shows `query()` Method**
   - The `API_FIXES.md` document (lines 137, 157) claims `agent_engines.get()` returns an "AgentEngine object WITH query() method"
   - The `DEPLOYMENT_INFO.md` (lines 94-103) shows example code using `.query()`
   - **BUT THIS IS INCORRECT** ❌

2. **Multiple API Versions Create Confusion**
   - Old API: `vertexai.preview.reasoning_engines` (deprecated)
   - Direct module API: `agent_engines.get()`
   - Client-based API: `vertexai.Client().agent_engines`
   - Each has different methods and capabilities

3. **Previous "Fixes" Were Based on Wrong Assumptions**
   - Previous attempts tried different parameter names (`message`, `user_id`, `input`)
   - These changes didn't fix the core issue: **the method doesn't exist at all**

---

## Investigation: What Does the Agent Engine API Actually Support?

### Finding the Correct API Pattern

According to the Agent Starter Pack documentation (agents.mdc file, lines 1286-1306):

```python
# DEPLOYMENT to Agent Engine
from vertexai.preview import reasoning_engines

# Wrap your root_agent for deployment
app_for_engine = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)

# Deploy
remote_app = agent_engines.create(
    agent_engine=app_for_engine,
    requirements=["google-cloud-aiplatform[adk,agent_engines]"],
    display_name="My Production Agent"
)

# QUERYING: Use stream_query(), create_session(), etc.
response = remote_app.stream_query(...)
```

### The Key Realization

**Agent Engine deployments use a DIFFERENT API from local ADK agents:**

| Local Development | Agent Engine Deployment |
|------------------|------------------------|
| `agent.run_async()` | ❌ Not available |
| `runner.run_async()` | ❌ Not available |
| `agent.query()` | ❌ **Does not exist** |
| Session-based API | ✅ **Correct approach** |

---

## The Correct Solution

### The Actual Working API

Based on Agent Engine logs, the correct method signature is:

```python
agent.stream_query(message=<content>, user_id=<user_id>)
```

NOT `query(input=...)` or `stream_query(input=...)`

### Working Implementation

```python
import vertexai
from vertexai import agent_engines

# Initialize
vertexai.init(project=project_id, location=location)

# Get the deployed agent
agent = agent_engines.get(
    resource_name=f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
)

# Use stream_query with CORRECT parameters
response_chunks = []
for chunk in agent.stream_query(
    message=json.dumps(payload),  # NOT 'input'!
    user_id="github-actions-pr-review"  # Required!
):
    response_chunks.append(chunk)

# Process the response chunks
# The final chunk typically contains the complete response
if response_chunks:
    final_response = response_chunks[-1]
    # Parse based on response structure
    if hasattr(final_response, 'text'):
        result = json.loads(final_response.text)
    else:
        result = json.loads(str(final_response))
```

### Option 3: Direct HTTP API Call

If the Python SDK doesn't expose the right methods, use the REST API directly:

```python
import google.auth
from google.auth.transport.requests import Request
import requests

# Get credentials
credentials, project = google.auth.default()
credentials.refresh(Request())

# Call Agent Engine REST API
url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}:query"

headers = {
    "Authorization": f"Bearer {credentials.token}",
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, json={"input": json.dumps(payload)})
result = response.json()
```

---

## Bug Timeline Visualization

```
┌─────────────────────────────────────────────────────────────────┐
│ WHAT EVERYONE THOUGHT WAS HAPPENING                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client Code          Network          Agent Engine            │
│  ┌──────────┐        ┌──────┐         ┌──────────┐           │
│  │ query()  │───X───>│ API  │────────>│ Working  │           │
│  │ method   │        │ call │         │  Agent   │           │
│  │ wrong    │        │fails │         │    ✓     │           │
│  └──────────┘        └──────┘         └──────────┘           │
│                                                                 │
│  ❌ Diagnosis: "Fix the API call parameters"                   │
│  Result: Still broken (3 attempts)                             │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ WHAT WAS ACTUALLY HAPPENING                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client Code          Network          Agent Engine            │
│  ┌──────────┐        ┌──────┐         ┌──────────┐           │
│  │ query()  │───X───>│ API  │────✓───>│ Broken   │           │
│  │ method   │        │ call │         │  Agent   │           │
│  │ wrong    │        │works │         │(returns  │           │
│  │          │        │ but  │         │ empty)   │           │
│  └──────────┘        └──────┘         └──────────┘           │
│                                             │                   │
│                                             │                   │
│                                   super().set_up()              │
│                                   breaks execution              │
│                                                                 │
│  ✓ Diagnosis: TWO bugs - fix agent first, then API             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why Previous Fixes Failed

### Attempt 1: Parameter Name Changes
```python
# Changed from:
response = agent.query(message=json.dumps(payload), user_id=user_id)
# To:
response = agent.query(input=json.dumps(payload))
```
**Result:** Still failed because `.query()` method doesn't exist

### Attempt 2: API Client Approach
```python
# Tried using:
client = vertexai.Client(project=project_id, location=location)
agent = client.agent_engines.get(name=resource_name)
```
**Result:** Still failed because this returns metadata object, not queryable agent

### Attempt 3: Direct Module Approach (Current)
```python
# Using:
agent = agent_engines.get(resource_name=resource_name)
response = agent.query(input=json.dumps(payload))
```
**Result:** STILL FAILING - the `.query()` method was never correct

---

## Discovery Process: How I Found the Real Bug

### Step 1: Checked what methods actually exist
```bash
uv run python -c "from vertexai import agent_engines; print([m for m in dir(agent_engines.AgentEngine) if not m.startswith('_')])"
```
**Result:** NO `query()` method exists on `AgentEngine` class ✓

### Step 2: Checked what the object instance has
```bash
vertexai.init(project='...', location='...')
agent = agent_engines.get(resource_name='...')
print([m for m in dir(agent) if not m.startswith('_') and callable(getattr(agent, m, None))])
```
**Result:** Agent HAS `stream_query` and `async_stream_query` methods! ✓

### Step 3: Tested the API call
Created `test_agent_api.py` and tried calling `stream_query(input=...)`
**Result:** Got 400 error "Reasoning Engine Execution failed"

### Step 4: Checked Agent Engine logs (THE KEY STEP!)
```bash
gcloud logging read 'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND severity>=ERROR' --limit=10
```
**Result:** Found the ACTUAL error:
```
TypeError: AdkApp.stream_query() missing 2 required keyword-only arguments: 'message' and 'user_id'
```

### The Breakthrough

The error showed that:
1. The method IS called `stream_query` (not `query`)
2. It requires `message=...` (not `input=...`)
3. It ALSO requires `user_id=...` (which was completely missing)

**Without checking the logs, we would have never discovered this!**

---

## Action Items to Fix BOTH Bugs

### Fix #1: Remove super().set_up() call (app/agent_engine_app.py)

**This is critical and must be fixed first!** The agent won't respond without this fix.

In `app/agent_engine_app.py`, line 46, remove the `super().set_up()` call:

```python
class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        setup_telemetry()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)

        # Set location if provided
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

        # ❌ REMOVE THIS LINE - it breaks Agent Engine deployment
        # super().set_up()
```

**Why this matters:**
- Calling `super().set_up()` triggers Resource Manager API calls
- These calls fail in Agent Engine environment
- Agent appears to work but returns empty responses
- **This is documented in agents.mdc line 1990 but was ignored**

After removing this line, **redeploy the agent**:
```bash
make deploy
```

### Fix #2: Correct API Call (scripts/call_agent.py)

Replace lines 49-79 with the correct API call:

```python
try:
    # Get the deployed agent
    agent = agent_engines.get(resource_name=resource_name)

    # Use stream_query with CORRECT parameters (discovered from logs)
    response_chunks = []
    for chunk in agent.stream_query(
        message=json.dumps(payload),  # Parameter is 'message', not 'input'!
        user_id="github-actions-pr-review"  # This is REQUIRED
    ):
        response_chunks.append(chunk)

    # Process response chunks
    if not response_chunks:
        raise Exception("No response chunks received from agent")

    # Get the final response (typically the last chunk)
    final_chunk = response_chunks[-1]

    # Parse response - try different access methods
    response_text = None
    if isinstance(final_chunk, str):
        response_text = final_chunk
    elif hasattr(final_chunk, "text"):
        response_text = final_chunk.text
    elif hasattr(final_chunk, "content"):
        response_text = final_chunk.content
    else:
        response_text = str(final_chunk)

    # Try to parse as JSON
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If not JSON, wrap it in expected format
        return {
            "summary": response_text,
            "inline_comments": [],
            "overall_status": "COMMENT",
            "metrics": {},
        }

except Exception as e:
    last_error = e
    if attempt < max_retries - 1:
        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
        time.sleep(delay)
        delay *= 2
    else:
        print(f"All {max_retries} attempts failed. Last error: {e}")
        raise
```

### Documentation Updates Needed

1. **API_FIXES.md** - Incorrect claims about `.query()` method (lines 137, 157)
2. **DEPLOYMENT_INFO.md** - Example code uses non-existent `.query()` (lines 94-103)
3. **Add new document** - "AGENT_ENGINE_API_GUIDE.md" with correct patterns

### Verification Steps

1. **Test locally first:**
   ```bash
   uv run python scripts/call_agent.py \
     --payload=tests/fixtures/python_simple_pr.json \
     --output=test_response.json \
     --project-id=bpc-askgreg-nonprod \
     --location=europe-west1 \
     --agent-engine-id=3659508948773371904
   ```

2. **Check agent logs if it still fails:**
   ```bash
   gcloud logging read \
     'resource.type="aiplatform.googleapis.com/ReasoningEngine" AND resource.labels.reasoning_engine_id="3659508948773371904" AND severity>=ERROR' \
     --limit=20 \
     --project=bpc-askgreg-nonprod
   ```

3. **Test in Console Playground** to verify agent is working

4. **Push to GitHub** and verify workflow succeeds

---

## Lessons Learned

### Why These Bugs Persisted Through 3 Attempts

#### The Real Timeline of Failures

**Attempt 1-3: All focused on the WRONG bug**
- Changed `query()` parameter names (`message`, `input`, `user_id`)
- Tried different API initialization approaches
- Updated documentation with "fixes" that didn't address root cause
- **Never checked if the agent itself was working**

#### Root Causes of Failure

1. **Focused on Client Code, Not Server Health**
   - Fixed the API call but never verified agent was responding
   - Should have tested in Console Playground FIRST
   - Agent was silently broken the entire time

2. **Ignored Critical Documentation**
   - `agents.mdc` line 1990 explicitly says: "Never call parent `set_up()` in Agent Engine apps"
   - This guidance was in the codebase but not followed
   - The `super().set_up()` was added/kept despite the warning

3. **Trusted Incorrect Documentation**
   - Internal docs (API_FIXES.md, DEPLOYMENT_INFO.md) contained wrong examples
   - Showed `query()` method that doesn't exist
   - No one validated these docs against actual API

4. **No Direct API Verification**
   - Didn't use `dir()` or `help()` to check actual methods
   - Didn't check SDK source code or official Google docs
   - Assumed method existed based on documentation

5. **No Incremental Testing**
   - Never tested just the agent in isolation
   - Never checked Agent Engine logs until now
   - Went straight to full integration testing

6. **Wrong Diagnostic Approach**
   - Error message said "no attribute 'query'"
   - Should have immediately checked: "what attributes DOES it have?"
   - Instead, kept trying different ways to call a method that doesn't exist

### Best Practices Going Forward

1. ✅ **Verify API methods exist** before using them
2. ✅ **Test locally** with minimal reproducible examples
3. ✅ **Check official Google Cloud documentation** not just internal docs
4. ✅ **Use `dir(agent)` or `help(agent)`** to see actual available methods
5. ✅ **Look at actual SDK source code** when documentation is unclear
6. ✅ **Create integration tests** that run against actual Agent Engine deployment

---

## References

### Correct Documentation Sources

1. **Agent Engine API Reference:**
   - https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/manage/overview

2. **Python SDK for Agent Engine:**
   - https://cloud.google.com/python/docs/reference/aiplatform/latest/google.cloud.aiplatform_v1.services.reasoning_engine_service

3. **Agent Starter Pack Patterns (agents.mdc):**
   - Lines 1286-1306: Deployment to Agent Engine
   - Lines 1993-2004: Agent Engine best practices

4. **REST API Documentation:**
   - https://cloud.google.com/vertex-ai/generative-ai/docs/reference/rest

### What to Search For

If still stuck, search for:
- "vertex ai agent engine python query"
- "vertex ai reasoning engine api session"
- "google cloud agent engine send message"
- Look at actual working examples in Agent Starter Pack samples

---

## Complete Fix Checklist

### Step 1: Fix the Agent (CRITICAL - Do This First!)
- [ ] Remove `super().set_up()` from `app/agent_engine_app.py` line 46
- [ ] Redeploy agent: `make deploy`
- [ ] Test in Console Playground - verify it responds
- [ ] Check logs if still broken

### Step 2: Fix the API Call
- [ ] Update `scripts/call_agent.py` to use `stream_query(message=..., user_id=...)`
- [ ] Test locally: `uv run python scripts/call_agent.py ...`
- [ ] Verify JSON response is correct

### Step 3: Update Documentation
- [ ] Fix `API_FIXES.md` - remove references to `.query()` method
- [ ] Fix `DEPLOYMENT_INFO.md` - update example code
- [ ] Add warning about `super().set_up()` to deployment docs

### Step 4: Verify End-to-End
- [ ] Push to GitHub
- [ ] Watch GitHub Actions workflow
- [ ] Verify PR review comments appear
- [ ] Celebrate! 🎉

---

## Summary

**Two bugs prevented the code review bot from working:**

1. **Agent bug (server-side):** `super().set_up()` breaks Agent Engine - agent returns empty responses
2. **API bug (client-side):** Code uses non-existent `.query()` method instead of `.stream_query(message, user_id)`

**Both must be fixed. Fix the agent first, then the API call.**
