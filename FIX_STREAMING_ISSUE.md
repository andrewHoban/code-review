# Fix for "No Response Chunks Received" Error

## Problem

The agent streaming was completing successfully but producing zero chunks, resulting in this error:

```
ERROR: No response chunks received from agent stream.
```

This error occurred because:
1. The `publisher_agent` was configured with `output_key="code_review_output"`
2. When an ADK agent has an `output_key`, it saves output to state but **may not stream it as text**
3. The client expects streamable text chunks, not just state updates
4. Result: Stream completed with no chunks → error

## Root Cause

From `app/agent.py`:

```python
publisher_agent = create_routed_agent(
    name="ReviewPublisher",
    ...
    output_key="code_review_output",  # ❌ This caused the issue
)
```

The `output_key` parameter in ADK agents causes output to be captured to state, but the Agent Engine streaming API expects actual text output that can be streamed to clients.

## Solution

**Removed `output_key` from the publisher agent** to ensure it produces streamable text output.

### Changes Made

1. **`app/agent.py`**: Removed `output_key="code_review_output"` from `publisher_agent`
2. **`app/agent.py`**: Enhanced publisher instruction to emphasize text output requirement:
   - Added explicit "CRITICAL REQUIREMENT - YOU MUST OUTPUT TEXT" section
   - Added example of correct output format
   - Emphasized no markdown fences, no extra commentary
   - Made it clear that failure to output text will cause the "no response chunks" error

### How It Works Now

1. **Publisher Agent** outputs JSON as plain text (no `output_key`)
2. **Stream Extractor** receives text chunks via `extract_text_and_state()`
3. **`coerce_review_output()`** parses JSON from text using `_extract_json_from_text()`
4. Client receives the parsed review output

### Fallback Chain

The `coerce_review_output()` function has this priority:
1. `code_review_output` in state (won't exist now, but safe to check)
2. `formatted_output` in state (fallback)
3. **JSON parsed from text** ← This is what we use now
4. Plain text wrapped as COMMENT (last resort)

## Testing

The fix should:
- ✅ Produce streamable text chunks
- ✅ Parse JSON from text successfully
- ✅ Not break existing tests (publisher agent wasn't directly tested)
- ✅ Maintain backward compatibility with state-based extraction

## Deployment

After deploying this fix:
1. The agent will output JSON as text
2. The stream will contain text chunks
3. The error "No response chunks received" should not occur
4. The GitHub workflow will receive valid review output

## Prevention

To prevent this in the future:
1. **Avoid `output_key` on final/publisher agents** that need to stream to clients
2. Use `output_key` only for intermediate agents that write to state
3. Always ensure final output is produced as **text**, not just state
4. Test streaming with actual Agent Engine deployment before merging
