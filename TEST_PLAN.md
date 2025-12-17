# Test Plan: Structured Output API Testing

## Overview

This test verifies that the simplified parsing logic works correctly with the Agent Engine API, both before and after deploying the `output_schema` changes.

## Test Scenarios

### Scenario 1: Test Current Deployment (Backward Compatibility)

**Purpose:** Verify the simplified parsing logic can handle current agent responses.

**Steps:**
1. Run test against currently deployed agent (without `output_schema`)
2. Verify parsing logic can extract response (may use fallback)
3. Validate response structure

**Expected:**
- Parsing succeeds (may use text fallback)
- Response has required fields (may be wrapped in default structure)

### Scenario 2: Test After Deployment (Structured Output)

**Purpose:** Verify structured output works with `output_schema` configuration.

**Steps:**
1. Deploy agent with `output_schema=CodeReviewOutput`
2. Run test against newly deployed agent
3. Verify structured output is in `code_review_output` state key
4. Validate full schema compliance

**Expected:**
- Response extracted directly from `code_review_output` state
- All schema validations pass
- No fallback logic needed

## Running the Tests

### Prerequisites

```bash
# Activate virtual environment
source .venv/bin/activate

# Ensure you have GCP credentials configured
gcloud auth application-default login
```

### Test 1: Current Deployment

```bash
python test_structured_output_api.py \
  --project-id bpc-askgreg-nonprod \
  --location europe-west1 \
  --agent-engine-id 3659508948773371904 \
  --payload tests/fixtures/python_simple_pr.json
```

**What to check:**
- ✅ Test completes without errors
- ✅ Response is extracted (may use fallback)
- ✅ Response has basic structure

### Test 2: After Deployment

**First, deploy the agent:**
```bash
# Deploy agent with new output_schema configuration
python -m app.app_utils.deploy \
  --project-id bpc-askgreg-nonprod \
  --location europe-west1 \
  --display-name "Code Review Agent"
```

**Then run the test:**
```bash
python test_structured_output_api.py \
  --project-id bpc-askgreg-nonprod \
  --location europe-west1 \
  --agent-engine-id <NEW_AGENT_ENGINE_ID> \
  --payload tests/fixtures/python_simple_pr.json
```

**What to check:**
- ✅ Response extracted from `code_review_output` state key
- ✅ All schema validations pass
- ✅ No fallback logic used
- ✅ Response matches `CodeReviewOutput` model exactly

## Test Validation

The test script validates:

1. **Response Extraction**
   - ✅ Structured output found in state
   - ✅ No parsing errors

2. **Required Fields**
   - ✅ `summary` (string)
   - ✅ `overall_status` (enum: APPROVED, NEEDS_CHANGES, COMMENT)
   - ✅ `inline_comments` (array)
   - ✅ `metrics` (object)

3. **Schema Compliance**
   - ✅ Pydantic model validation passes
   - ✅ Enum values are valid
   - ✅ Data types are correct
   - ✅ Nested structures validated

4. **Inline Comments Structure**
   - ✅ Each comment has `path`, `line`, `severity`, `body`
   - ✅ Severity is valid enum value

5. **Metrics Structure**
   - ✅ All required metric fields present
   - ✅ All metrics are integers

## Success Criteria

### Before Deployment
- ✅ Test runs without errors
- ✅ Response can be parsed (even if using fallback)
- ✅ Basic structure is present

### After Deployment
- ✅ Response extracted from `code_review_output` state
- ✅ All schema validations pass
- ✅ No fallback logic triggered
- ✅ Response is valid `CodeReviewOutput` instance

## Troubleshooting

### Issue: "No structured output found"

**Possible causes:**
- Agent not deployed with `output_schema`
- State key name mismatch
- Agent response format changed

**Solution:**
- Check agent deployment configuration
- Verify `output_key="code_review_output"` in agent config
- Check agent logs for errors

### Issue: "Schema validation failed"

**Possible causes:**
- Agent returning unexpected format
- Missing required fields
- Invalid enum values

**Solution:**
- Check response structure in saved JSON file
- Verify agent instructions match expected output
- Review agent logs for generation issues

### Issue: "Failed to retrieve agent"

**Possible causes:**
- Wrong project/location/agent-engine-id
- Missing GCP credentials
- Agent not deployed

**Solution:**
- Verify credentials: `gcloud auth application-default login`
- Check agent exists in GCP Console
- Verify project ID and location

## Next Steps

After successful testing:

1. ✅ Verify all tests pass
2. ✅ Review response quality
3. ✅ Check for any edge cases
4. ✅ Monitor production logs after deployment
5. ✅ Remove fallback logic after 1-2 weeks of stability
