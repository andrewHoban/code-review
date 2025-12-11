"""Test the CORRECT Agent Engine API based on error log findings."""

import json

import vertexai
from vertexai import agent_engines

print("=" * 70)
print("Testing CORRECT Agent Engine API")
print("=" * 70)
print()

# Initialize
vertexai.init(project="bpc-askgreg-nonprod", location="europe-west1")

# Get the deployed agent
agent = agent_engines.get(
    resource_name="projects/442593217095/locations/europe-west1/reasoningEngines/3659508948773371904"
)

print("✓ Successfully retrieved agent")
print(f"Agent display name: {agent.display_name}")
print()

# Load test payload
with open("tests/fixtures/python_simple_pr.json") as f:
    payload = json.load(f)

print("✓ Loaded test payload")
print(f"PR number: {payload.get('pr_metadata', {}).get('pr_number', 'unknown')}")
print()

# Call with CORRECT parameters based on error logs
print("Calling agent.stream_query() with correct parameters:")
print("  - message=json.dumps(payload)")
print("  - user_id='github-actions-pr-review'")
print()

try:
    response_chunks = []
    for i, chunk in enumerate(
        agent.stream_query(
            message=json.dumps(payload), user_id="github-actions-pr-review"
        )
    ):
        response_chunks.append(chunk)
        print(f"Received chunk {i+1}: {type(chunk)}")
        if i == 0:
            # Show first chunk details
            print(f"  First chunk sample: {str(chunk)[:200]}...")

    print()
    print(f"✓ Received {len(response_chunks)} total chunks")
    print()

    # Process final response
    if response_chunks:
        final_chunk = response_chunks[-1]
        print(f"Final chunk type: {type(final_chunk)}")

        # Try to extract text
        response_text = None
        if isinstance(final_chunk, str):
            response_text = final_chunk
            print("Response is a string")
        elif hasattr(final_chunk, "text"):
            response_text = final_chunk.text
            print("Response has .text attribute")
        elif hasattr(final_chunk, "content"):
            response_text = final_chunk.content
            print("Response has .content attribute")
        else:
            response_text = str(final_chunk)
            print("Response converted to string")

        print()
        print("=" * 70)
        print("RESPONSE TEXT (first 500 chars):")
        print("=" * 70)
        print(response_text[:500] if response_text else "None")
        print()

        # Try to parse as JSON
        try:
            result = json.loads(response_text) if response_text else None
            print("✓ Successfully parsed as JSON")
            print()
            print("Response structure:")
            print(
                f"  - Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
            )
            if isinstance(result, dict):
                if "summary" in result:
                    print(f"  - Summary length: {len(result.get('summary', ''))}")
                if "inline_comments" in result:
                    print(
                        f"  - Inline comments: {len(result.get('inline_comments', []))}"
                    )
                if "overall_status" in result:
                    print(f"  - Status: {result.get('overall_status')}")

            # Write to file
            with open("test_response_correct.json", "w") as f:
                json.dump(result, f, indent=2)
            print()
            print("✓ Response written to test_response_correct.json")

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse as JSON: {e}")
            print("Response text:")
            print(response_text)

    print()
    print("=" * 70)
    print("✅ SUCCESS! The agent responded correctly.")
    print("=" * 70)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
