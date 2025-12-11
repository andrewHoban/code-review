# Quick Fix Guide - Code Review Bot

## The Problem

Your code review bot has **TWO bugs** preventing it from working:

1. 🔴 **Agent returns empty responses** (even in Console Playground)
2. 🔴 **API call uses wrong method/parameters**

## The Quick Fix

### Fix 1: Make Agent Respond (app/agent_engine_app.py)

**Line 46 - DELETE THIS LINE:**

```python
# ❌ DELETE THIS
super().set_up()
```

**Why:** This line breaks Agent Engine execution (documented in agents.mdc line 1990)

### Fix 2: Use Correct API (scripts/call_agent.py)

**Lines 50-53 - CHANGE FROM:**

```python
agent = agent_engines.get(resource_name=resource_name)
response = agent.query(input=json.dumps(payload))  # ❌ Wrong
```

**TO:**

```python
agent = agent_engines.get(resource_name=resource_name)

# Collect streaming response
response_chunks = []
for chunk in agent.stream_query(
    message=json.dumps(payload),  # ✓ Correct parameter name
    user_id="github-actions"       # ✓ Required parameter
):
    response_chunks.append(chunk)

# Get final response
if response_chunks:
    final_chunk = response_chunks[-1]
    response_text = (
        final_chunk if isinstance(final_chunk, str)
        else final_chunk.text if hasattr(final_chunk, "text")
        else str(final_chunk)
    )
```

## Deploy & Test

```bash
# 1. Redeploy the agent
make deploy

# 2. Test in Console Playground
# https://console.cloud.google.com/vertex-ai/agents/locations/europe-west1/agent-engines/3659508948773371904/playground?project=bpc-askgreg-nonprod

# 3. Test the API call
uv run python scripts/call_agent.py \
  --payload=tests/fixtures/python_simple_pr.json \
  --output=test_response.json \
  --project-id=bpc-askgreg-nonprod \
  --location=europe-west1 \
  --agent-engine-id=3659508948773371904

# 4. Verify response
cat test_response.json

# 5. Push to GitHub
git add . && git commit -m "fix: correct agent API and remove super().set_up()" && git push
```

## What Went Wrong Before

**3 previous attempts all fixed the wrong bug:**
- Changed API parameters but agent was broken
- Never tested agent in isolation
- Trusted incorrect documentation

**The breakthrough came from:**
- Checking actual Agent Engine logs
- Testing in Console Playground
- Reading the Agent Starter Pack guidance about `super().set_up()`

## See Full Analysis

Read `BUG_ANALYSIS.md` for complete details on:
- How the bugs were discovered
- Why previous fixes failed
- Lessons learned for future debugging
