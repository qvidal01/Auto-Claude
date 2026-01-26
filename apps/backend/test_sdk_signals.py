#!/usr/bin/env python3
"""
Test script to inspect Claude Agent SDK message signals.

This script helps us understand exactly what messages and signals we receive
from the SDK when an agent stops responding. We want to find a reliable way
to know if the agent is:
1. Waiting for user input (question asked)
2. Done with the task (phase complete)

Run from apps/backend/:
    python test_sdk_signals.py
"""

import asyncio
import json
from pathlib import Path

from core.client import create_client


async def test_sdk_signals():
    """Test what signals we get from the SDK."""

    # Use a temp directory for testing
    project_dir = Path.cwd()
    spec_dir = project_dir / ".auto-claude" / "specs" / "test-sdk-signals"
    spec_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("SDK SIGNAL TEST")
    print("=" * 80)
    print(f"Project dir: {project_dir}")
    print(f"Spec dir: {spec_dir}")
    print()

    # Create a client - using coder type for full capabilities
    client = create_client(
        project_dir,
        spec_dir,
        model="claude-haiku-4-5-20251001",  # Use Haiku for speed/cost
        agent_type="coder",
        max_thinking_tokens=None,
    )

    # Test prompt that should result in questions
    test_prompt = """
You are helping plan a simple web application.

Before you start implementing anything, I need you to ask me a few clarifying questions about:
1. What framework should we use?
2. What database do you prefer?
3. Should we include authentication?

Please ask these questions and wait for my response before proceeding.
"""

    print("SENDING TEST PROMPT:")
    print("-" * 40)
    print(test_prompt)
    print("-" * 40)
    print()

    all_messages = []

    try:
        async with client:
            await client.query(test_prompt)

            print("RECEIVING RESPONSE STREAM:")
            print("-" * 40)

            msg_index = 0
            async for msg in client.receive_response():
                msg_index += 1
                msg_type = type(msg).__name__

                # Collect all attributes of the message
                msg_attrs = {}
                for attr in dir(msg):
                    if not attr.startswith('_'):
                        try:
                            val = getattr(msg, attr)
                            if not callable(val):
                                # Try to serialize, fall back to str
                                try:
                                    json.dumps(val)
                                    msg_attrs[attr] = val
                                except (TypeError, ValueError):
                                    msg_attrs[attr] = str(val)
                        except Exception as e:
                            msg_attrs[attr] = f"<error: {e}>"

                all_messages.append({
                    "index": msg_index,
                    "type": msg_type,
                    "attributes": msg_attrs,
                })

                # Print summary
                print(f"\n[{msg_index}] MESSAGE TYPE: {msg_type}")
                print(f"    Attributes: {list(msg_attrs.keys())}")

                # Print key attributes based on type
                if msg_type == "ResultMessage":
                    print(f"    >>> RESULT MESSAGE <<<")
                    print(f"    subtype: {msg_attrs.get('subtype', 'N/A')}")
                    print(f"    total_cost_usd: {msg_attrs.get('total_cost_usd', 'N/A')}")
                    print(f"    duration_ms: {msg_attrs.get('duration_ms', 'N/A')}")
                    print(f"    ALL ATTRS: {json.dumps(msg_attrs, indent=6, default=str)}")

                elif msg_type == "AssistantMessage":
                    content = msg_attrs.get('content', [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                if block.get('type') == 'text':
                                    text = block.get('text', '')[:200]
                                    print(f"    Text: {text}...")
                            elif hasattr(block, 'text'):
                                print(f"    Text: {block.text[:200]}...")
                            elif hasattr(block, 'type'):
                                print(f"    Block type: {block.type}")

                elif "system" in msg_type.lower():
                    print(f"    >>> SYSTEM MESSAGE <<<")
                    print(f"    ALL ATTRS: {json.dumps(msg_attrs, indent=6, default=str)}")

                # Check for any 'subtype' attribute
                if 'subtype' in msg_attrs:
                    print(f"    !!! SUBTYPE FOUND: {msg_attrs['subtype']} !!!")

                # Check for any 'stop' related attributes
                for key in msg_attrs:
                    if 'stop' in key.lower() or 'end' in key.lower() or 'complete' in key.lower():
                        print(f"    !!! {key}: {msg_attrs[key]} !!!")

            print("\n" + "-" * 40)
            print("STREAM ENDED")
            print("-" * 40)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total messages received: {len(all_messages)}")
    print()
    print("Message types received:")
    type_counts = {}
    for msg in all_messages:
        t = msg['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, count in sorted(type_counts.items()):
        print(f"  - {t}: {count}")

    # Check for ResultMessage specifically
    result_msgs = [m for m in all_messages if m['type'] == 'ResultMessage']
    if result_msgs:
        print("\nResultMessage details:")
        for rm in result_msgs:
            print(f"  Index: {rm['index']}")
            print(f"  Attributes: {json.dumps(rm['attributes'], indent=4, default=str)}")
    else:
        print("\nNo ResultMessage received!")

    # Save full log
    log_file = spec_dir / "sdk_signal_log.json"
    with open(log_file, 'w') as f:
        json.dump(all_messages, f, indent=2, default=str)
    print(f"\nFull log saved to: {log_file}")

    return all_messages


async def test_completion_scenario():
    """Test what signals we get when the agent completes a task."""

    project_dir = Path.cwd()
    spec_dir = project_dir / ".auto-claude" / "specs" / "test-sdk-signals"
    spec_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("COMPLETION SCENARIO TEST")
    print("=" * 80)

    client = create_client(
        project_dir,
        spec_dir,
        model="claude-haiku-4-5-20251001",
        agent_type="coder",
        max_thinking_tokens=None,
    )

    # Test prompt that should result in completion (no questions)
    test_prompt = """
What is 2 + 2? Just give me the answer, nothing else.
"""

    print("SENDING COMPLETION TEST PROMPT:")
    print("-" * 40)
    print(test_prompt)
    print("-" * 40)

    all_messages = []

    try:
        async with client:
            await client.query(test_prompt)

            msg_index = 0
            async for msg in client.receive_response():
                msg_index += 1
                msg_type = type(msg).__name__

                msg_attrs = {}
                for attr in dir(msg):
                    if not attr.startswith('_'):
                        try:
                            val = getattr(msg, attr)
                            if not callable(val):
                                try:
                                    json.dumps(val)
                                    msg_attrs[attr] = val
                                except (TypeError, ValueError):
                                    msg_attrs[attr] = str(val)
                        except:
                            pass

                all_messages.append({
                    "index": msg_index,
                    "type": msg_type,
                    "attributes": msg_attrs,
                })

                print(f"[{msg_index}] {msg_type}")
                if msg_type == "ResultMessage":
                    print(f"    subtype: {msg_attrs.get('subtype', 'N/A')}")
                elif msg_type == "AssistantMessage":
                    content = msg_attrs.get('content', [])
                    if hasattr(msg, 'content'):
                        for block in msg.content:
                            if hasattr(block, 'text'):
                                print(f"    Text: {block.text}")

            print("\nSTREAM ENDED - COMPLETION SCENARIO")

    except Exception as e:
        print(f"ERROR: {e}")

    # Compare
    print("\nMessage types in completion scenario:")
    for msg in all_messages:
        print(f"  - {msg['type']}")

    return all_messages


if __name__ == "__main__":
    print("Running SDK signal tests...\n")

    # Run tests
    asyncio.run(test_sdk_signals())
    asyncio.run(test_completion_scenario())

    print("\n" + "=" * 80)
    print("TESTS COMPLETE")
    print("=" * 80)
    print("""
KEY QUESTIONS TO ANSWER:
1. Is there a ResultMessage at the end?
2. Does ResultMessage have a 'subtype' that indicates completion vs waiting?
3. Are there any other signals that differentiate the two scenarios?
4. Can we rely on any structural signal from the SDK?
""")
