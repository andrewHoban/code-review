"""Simple test to see if agent responds at all."""

import vertexai
from vertexai import agent_engines

vertexai.init(project="bpc-askgreg-nonprod", location="europe-west1")
agent = agent_engines.get(
    resource_name="projects/442593217095/locations/europe-west1/reasoningEngines/3659508948773371904"
)

print("Testing with simple message...")
print("=" * 60)

try:
    chunks = []
    for i, chunk in enumerate(
        agent.stream_query(message="Hello, can you hear me?", user_id="test-user")
    ):
        chunks.append(chunk)
        print(f"Chunk {i + 1}: {type(chunk)}")
        if hasattr(chunk, "text"):
            print(f"  Text: {chunk.text[:200]}")
        else:
            print(f"  Content: {str(chunk)[:200]}")
        if i > 10:
            print("... (stopping after 10 chunks)")
            break

    print(f"\nTotal chunks: {len(chunks)}")
    if chunks:
        print(f"Last chunk type: {type(chunks[-1])}")
        print(f"Last chunk: {chunks[-1]}")
    else:
        print("⚠️  No chunks received!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
