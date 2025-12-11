# Deployment Notes: Fix for Agent Streaming Issue

## What Was Fixed

Fixed the "No response chunks received from agent stream" error that was preventing the code review agent from producing output.

## Changes Made

### 1. `app/agent.py` - Publisher Agent Configuration

**Before:**
```python
publisher_agent = create_routed_agent(
    name="ReviewPublisher",
    ...
    output_key="code_review_output",  # This prevented text streaming
)
```

**After:**
```python
publisher_agent = create_routed_agent(
    name="ReviewPublisher",
    ...
    # Don't use output_key - we need the JSON to be streamed as text, not just saved to state
    # The stream_extractor will parse the JSON from the streamed text
)
```

### 2. `app/agent.py` - Enhanced Publisher Instructions

Added explicit guidance to ensure the agent outputs text:

```
CRITICAL REQUIREMENT - YOU MUST OUTPUT TEXT:
Your response MUST contain the JSON object as actual text that will be streamed to the client. This is NOT optional.
Start your response immediately with the opening brace '{' of the JSON object.
Do NOT wrap it in markdown code fences (no ```json).
Do NOT add any explanatory text before or after the JSON.
The system will automatically save your output to state AND stream it to the client.
If you produce no text output, the agent will fail with "no response chunks received".
```

## Why This Fix Works

### The Problem

When an ADK agent is configured with `output_key`, it:
1. Captures the agent's output
2. Saves it to the session state under that key
3. **May not produce streamable text chunks** for the client

The Agent Engine streaming API (`stream_query()`) expects to yield text chunks that can be consumed by the client. When an agent only updates state without producing text, the stream completes successfully but yields zero chunks, causing the error.

### The Solution

By removing `output_key`, we force the publisher agent to:
1. Output JSON as plain text (which gets streamed)
2. Allow the `stream_extractor` to parse it from the text

### How Data Flows Now

```
┌─────────────────────┐
│  Publisher Agent    │
│  (no output_key)    │
└──────────┬──────────┘
           │
           ├─ Outputs JSON as text
           │
           v
┌─────────────────────┐
│   Agent Engine      │
│   stream_query()    │
└──────────┬──────────┘
           │
           ├─ Streams text chunks to client
           │
           v
┌─────────────────────┐
│ extract_text_and_   │
│ state()             │
└──────────┬──────────┘
           │
           ├─ Combines all text chunks
           │
           v
┌─────────────────────┐
│ coerce_review_      │
│ output()            │
└──────────┬──────────┘
           │
           ├─ Parses JSON from text
           │
           v
┌─────────────────────┐
│  Valid Review       │
│  Output             │
└─────────────────────┘
```

## Deployment Checklist

- [x] Fix implemented in `app/agent.py`
- [x] All integration tests pass
- [x] All unit tests pass
- [x] Stream extractor tests pass
- [ ] Deploy to staging environment
- [ ] Test with actual PR payload
- [ ] Verify streaming produces text chunks
- [ ] Deploy to production

## Testing After Deployment

After deploying, verify the fix by:

1. **Check Agent Engine logs** for successful streaming:
   ```
   Streaming started (timeout: 600s)...
   Received 1 chunks (elapsed: 2.3s) - latest: chunk with text: {"summary": ...
   Streaming completed: 1 chunks received in 2.3s
   ```

2. **Check GitHub workflow output** for successful review:
   ```
   Processing 1 chunks to extract final response...
   Debug: Extracted text length=1234, state_delta_keys=[]
   ```

3. **Verify PR comment is posted** with review content

## What If It Still Fails?

If the error persists, check:

1. **Agent instruction compliance**: The model might still be wrapping output in markdown fences
   - Look for `\`\`\`json` in the output
   - The `_strip_json_fence()` function should handle this, but it's better to avoid it

2. **Model behavior**: Codestral (the publisher model) might behave differently than expected
   - Check if it's outputting anything at all
   - Enable `CODE_REVIEW_DUMP_CHUNKS` env var to see raw chunks

3. **ADK version**: Ensure ADK version is compatible with streaming
   - Check `pyproject.toml` for ADK version
   - Verify Agent Engine SDK version matches deployment

## Rollback Plan

If the fix causes issues, rollback by:

1. Restore `output_key="code_review_output"` in `app/agent.py`
2. Update `coerce_review_output()` to require state-based output
3. Investigate alternative approaches (e.g., custom streaming handler)

## Alternative Approaches (Not Used)

We considered but didn't implement:

1. **Keep `output_key` and force text output**: Would require ADK changes
2. **Custom streaming handler**: More complex, not needed
3. **Dual output (state + text)**: ADK doesn't support this pattern well

The chosen solution (remove `output_key`) is the simplest and most reliable approach for ensuring streamable text output.
