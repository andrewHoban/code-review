# Deployment Information

## ✅ Deployment Successful

**Date:** December 11, 2025  
**Project:** `bpc-askgreg-nonprod`  
**Location:** `europe-west1`  
**Agent Engine ID:** `3659508948773371904`

## Resource Details

**Full Resource Name:**
```
projects/442593217095/locations/europe-west1/reasoningEngines/3659508948773371904
```

**Service Account:**
```
service-442593217095@gcp-sa-aiplatform-re.iam.gserviceaccount.com
```

## Configuration

- **Display Name:** `code-review`
- **Min Instances:** 1
- **Max Instances:** 10
- **CPU:** 4 cores
- **Memory:** 8Gi
- **Container Concurrency:** 9

## Environment Variables

- `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY`: true
- `GOOGLE_CLOUD_REGION`: europe-west1
- `NUM_WORKERS`: 1
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`: true

## Access

### Console Playground
https://console.cloud.google.com/vertex-ai/agents/locations/europe-west1/agent-engines/3659508948773371904/playground?project=bpc-askgreg-nonprod

### Using the Agent Engine API

```python
import vertexai

client = vertexai.Client(
    project="bpc-askgreg-nonprod",
    location="europe-west1"
)

agent_engine = client.agent_engines.get(
    name='projects/442593217095/locations/europe-west1/reasoningEngines/3659508948773371904'
)
```

## Testing the Deployed Agent

### 1. Console Playground
Use the link above to test the agent interactively in the Google Cloud Console.

### 2. API Testing
Create a test script to call the agent:

```python
import json
import vertexai

client = vertexai.Client(
    project="bpc-askgreg-nonprod",
    location="europe-west1"
)

agent_engine = client.agent_engines.get(
    name='projects/442593217095/locations/europe-west1/reasoningEngines/3659508948773371904'
)

# Load test payload
with open('tests/fixtures/python_simple_pr.json') as f:
    payload = json.load(f)

# Query the agent
response = agent_engine.query(input=json.dumps(payload))

print(response)
```

### 3. GitHub Integration
Follow the integration guide in `docs/integration_guide.md` to connect this agent to GitHub Actions.

## Monitoring

### Cloud Trace
View traces and performance metrics:
https://console.cloud.google.com/traces/list?project=bpc-askgreg-nonprod

### Logs
View agent logs:
https://console.cloud.google.com/logs/query?project=bpc-askgreg-nonprod

## Next Steps

1. ✅ **Deployment Complete** - Agent is live
2. **Test in Console Playground** - Verify functionality
3. **Test with Real PR Data** - Use example payloads
4. **Set up GitHub Integration** - Connect to GitHub Actions
5. **Monitor Performance** - Check Cloud Trace for latency

## Updating the Deployment

To update the agent after making changes:

```bash
make deploy
```

The deployment script will update the existing agent engine instance.

## Troubleshooting

If you encounter issues:

1. Check logs in Cloud Console
2. Verify API is enabled (Vertex AI Agent Engine API)
3. Check service account permissions
4. Review Cloud Trace for errors

## Support

- Deployment metadata: `deployment_metadata.json`
- Integration guide: `docs/integration_guide.md`
- Testing guide: `docs/testing-guidelines.md`
