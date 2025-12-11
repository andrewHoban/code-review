"""Test script to discover the correct Agent Engine API."""

import json

import vertexai
from vertexai import agent_engines

# Initialize
vertexai.init(project="bpc-askgreg-nonprod", location="europe-west1")

# Get the deployed agent
agent = agent_engines.get(
    resource_name="projects/442593217095/locations/europe-west1/reasoningEngines/3659508948773371904"
)

print("✓ Successfully retrieved agent")
print(f"Agent type: {type(agent)}")
print(f"Agent name: {agent.display_name}")
print()

# Test 1: Try stream_query with a simple input
print("=" * 60)
print("TEST 1: stream_query with simple input")
print("=" * 60)

test_input = {"test": "hello from test script"}

try:
    print(f"Calling stream_query with input: {test_input}")
    result = agent.stream_query(input=json.dumps(test_input))
    print(f"Result type: {type(result)}")

    # Iterate through streaming response
    for i, chunk in enumerate(result):
        print(f"Chunk {i}: {type(chunk)} - {chunk}")
        if i > 5:  # Limit output
            print("... (truncated)")
            break
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e)}")

print()

# Test 2: Try with actual PR payload
print("=" * 60)
print("TEST 2: stream_query with PR payload")
print("=" * 60)

try:
    with open("tests/fixtures/python_simple_pr.json") as f:
        payload = json.load(f)

    print("Calling stream_query with PR payload")
    result = agent.stream_query(input=json.dumps(payload))

    # Collect all chunks
    chunks = []
    for chunk in result:
        chunks.append(chunk)
        if len(chunks) > 10:
            print(f"Received {len(chunks)} chunks so far...")

    print(f"✓ Received {len(chunks)} total chunks")
    print(f"First chunk type: {type(chunks[0])}")
    print(f"First chunk: {chunks[0]}")

    # Try to extract final response
    if chunks:
        last_chunk = chunks[-1]
        print(f"\nLast chunk: {last_chunk}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()

print()

# Test 3: Try session-based approach
print("=" * 60)
print("TEST 3: Session-based approach")
print("=" * 60)

try:
    session = agent.create_session(user_id="test_user")
    print(f"✓ Created session: {session}")
    print(f"Session type: {type(session)}")
except Exception as e:
    print(f"❌ Error creating session: {e}")
