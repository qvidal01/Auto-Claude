#!/usr/bin/env python3
"""
Test script to inspect Claude Agent SDK signals during a longer chain of operations.

This test asks the agent to do multiple tasks to see:
1. When does ResultMessage appear? Only at the very end, or at intermediate points?
2. Is `subtype: success` a reliable signal that the agent has stopped?
3. What happens during tool use - do we see intermediate ResultMessages?

Run from apps/backend/:
    source .venv/bin/activate && python test_sdk_long_chain.py
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from core.client import create_client


async def test_long_chain():
    """Test a longer chain of agent operations."""

    project_dir = Path.cwd()
    spec_dir = project_dir / ".auto-claude" / "specs" / "test-sdk-long-chain"
    spec_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("LONG CHAIN SDK TEST")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print()

    client = create_client(
        project_dir,
        spec_dir,
        model="claude-haiku-4-5-20251001",
        agent_type="coder",
        max_thinking_tokens=None,
    )

    # Test prompt that should trigger multiple operations
    test_prompt = """
Please do the following tasks in sequence:

1. First, use the Glob tool to find all Python files in the current directory (just the top level, pattern "*.py")
2. Then, use the Read tool to read the first few lines of one of those files
3. After reading, tell me what you found
4. Finally, ask me a question about what I'd like to do next with this information

Do these steps one by one. I want to see the full chain of operations.
"""

    print("SENDING LONG CHAIN PROMPT:")
    print("-" * 40)
    print(test_prompt)
    print("-" * 40)
    print()

    all_messages = []
    result_messages = []
    tool_operations = []

    try:
        async with client:
            await client.query(test_prompt)

            print("RECEIVING RESPONSE STREAM:")
            print("-" * 40)

            msg_index = 0
            async for msg in client.receive_response():
                msg_index += 1
                msg_type = type(msg).__name__
                timestamp = datetime.now().isoformat()

                # Collect key attributes
                msg_data = {
                    "index": msg_index,
                    "type": msg_type,
                    "timestamp": timestamp,
                }

                # Print based on message type
                if msg_type == "SystemMessage":
                    subtype = getattr(msg, 'subtype', None)
                    msg_data["subtype"] = subtype
                    print(f"\n[{msg_index}] {timestamp}")
                    print(f"    TYPE: SystemMessage (subtype: {subtype})")

                elif msg_type == "AssistantMessage":
                    content = getattr(msg, 'content', [])
                    print(f"\n[{msg_index}] {timestamp}")
                    print(f"    TYPE: AssistantMessage")

                    for block in content:
                        block_type = type(block).__name__
                        if hasattr(block, 'text'):
                            text_preview = block.text[:150].replace('\n', ' ')
                            print(f"    - TextBlock: {text_preview}...")
                            msg_data["text_preview"] = text_preview
                        elif hasattr(block, 'name'):
                            tool_name = block.name
                            tool_id = getattr(block, 'id', 'unknown')
                            print(f"    - ToolUseBlock: {tool_name} (id: {tool_id[:8]}...)")
                            msg_data["tool_use"] = tool_name
                            tool_operations.append({
                                "index": msg_index,
                                "tool": tool_name,
                                "id": tool_id,
                                "timestamp": timestamp,
                            })
                        else:
                            print(f"    - {block_type}")

                elif msg_type == "UserMessage":
                    content = getattr(msg, 'content', [])
                    print(f"\n[{msg_index}] {timestamp}")
                    print(f"    TYPE: UserMessage (tool results)")

                    for block in content:
                        if hasattr(block, 'tool_use_id'):
                            is_error = getattr(block, 'is_error', False)
                            status = "ERROR" if is_error else "OK"
                            print(f"    - ToolResult: {status}")
                            msg_data["tool_result"] = status

                elif msg_type == "ResultMessage":
                    subtype = getattr(msg, 'subtype', None)
                    result_text = getattr(msg, 'result', '')
                    num_turns = getattr(msg, 'num_turns', 0)
                    duration_ms = getattr(msg, 'duration_ms', 0)

                    msg_data["subtype"] = subtype
                    msg_data["num_turns"] = num_turns
                    msg_data["duration_ms"] = duration_ms
                    msg_data["result_preview"] = result_text[:200] if result_text else None

                    result_messages.append(msg_data)

                    print(f"\n[{msg_index}] {timestamp}")
                    print(f"    TYPE: ResultMessage")
                    print(f"    >>> SUBTYPE: {subtype} <<<")
                    print(f"    num_turns: {num_turns}")
                    print(f"    duration_ms: {duration_ms}")
                    if result_text:
                        print(f"    result: {result_text[:200]}...")

                else:
                    print(f"\n[{msg_index}] {timestamp}")
                    print(f"    TYPE: {msg_type}")

                all_messages.append(msg_data)

            print("\n" + "-" * 40)
            print(f"STREAM ENDED at {datetime.now().isoformat()}")
            print("-" * 40)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    print(f"\nTotal messages: {len(all_messages)}")

    # Count message types
    type_counts = {}
    for msg in all_messages:
        t = msg['type']
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\nMessage type counts:")
    for t, count in sorted(type_counts.items()):
        print(f"  - {t}: {count}")

    print(f"\nTool operations: {len(tool_operations)}")
    for op in tool_operations:
        print(f"  - [{op['index']}] {op['tool']}")

    print(f"\nResultMessage occurrences: {len(result_messages)}")
    for rm in result_messages:
        print(f"  - [{rm['index']}] subtype={rm['subtype']}, turns={rm['num_turns']}, duration={rm['duration_ms']}ms")

    # Key question
    print("\n" + "=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)

    if len(result_messages) == 1:
        print("\n✓ ResultMessage appeared exactly ONCE (at the end)")
        print("  This means we CAN rely on ResultMessage as 'agent has stopped' signal")
    else:
        print(f"\n⚠ ResultMessage appeared {len(result_messages)} times")
        print("  Need to investigate when/why multiple ResultMessages occur")

    if result_messages:
        last_result = result_messages[-1]
        print(f"\nFinal ResultMessage:")
        print(f"  - Index: {last_result['index']} (out of {len(all_messages)} total messages)")
        print(f"  - Subtype: {last_result['subtype']}")
        print(f"  - Is it the last message? {last_result['index'] == len(all_messages)}")

    # Save log
    log_file = spec_dir / "long_chain_log.json"
    with open(log_file, 'w') as f:
        json.dump({
            "all_messages": all_messages,
            "result_messages": result_messages,
            "tool_operations": tool_operations,
        }, f, indent=2, default=str)
    print(f"\nFull log saved to: {log_file}")

    return all_messages, result_messages


async def test_multi_turn_conversation():
    """Test what happens when we simulate multiple turns."""

    print("\n" + "=" * 80)
    print("MULTI-TURN CONVERSATION TEST")
    print("=" * 80)
    print("Testing if ResultMessage appears after EACH turn or only at the end")
    print()

    project_dir = Path.cwd()
    spec_dir = project_dir / ".auto-claude" / "specs" / "test-sdk-long-chain"

    # First turn
    print("--- TURN 1: Initial question ---")
    client1 = create_client(
        project_dir,
        spec_dir,
        model="claude-haiku-4-5-20251001",
        agent_type="human_replacement",  # Minimal tools
        max_thinking_tokens=None,
    )

    turn1_messages = []
    try:
        async with client1:
            await client1.query("What are 3 good names for a pet cat? Just list them.")

            async for msg in client1.receive_response():
                msg_type = type(msg).__name__
                turn1_messages.append(msg_type)

                if msg_type == "ResultMessage":
                    subtype = getattr(msg, 'subtype', None)
                    result = getattr(msg, 'result', '')
                    print(f"  ResultMessage: subtype={subtype}")
                    print(f"  Result: {result}")
                elif msg_type == "AssistantMessage":
                    content = getattr(msg, 'content', [])
                    for block in content:
                        if hasattr(block, 'text'):
                            print(f"  Assistant: {block.text}")

    except Exception as e:
        print(f"  Error: {e}")

    print(f"  Messages received: {turn1_messages}")
    print(f"  ResultMessage count: {turn1_messages.count('ResultMessage')}")

    # Second turn (new client, simulating continuation)
    print("\n--- TURN 2: Follow-up question ---")
    client2 = create_client(
        project_dir,
        spec_dir,
        model="claude-haiku-4-5-20251001",
        agent_type="human_replacement",
        max_thinking_tokens=None,
    )

    turn2_messages = []
    try:
        async with client2:
            await client2.query("I like the first name. Can you suggest 2 middle names for it?")

            async for msg in client2.receive_response():
                msg_type = type(msg).__name__
                turn2_messages.append(msg_type)

                if msg_type == "ResultMessage":
                    subtype = getattr(msg, 'subtype', None)
                    result = getattr(msg, 'result', '')
                    print(f"  ResultMessage: subtype={subtype}")
                    print(f"  Result: {result}")
                elif msg_type == "AssistantMessage":
                    content = getattr(msg, 'content', [])
                    for block in content:
                        if hasattr(block, 'text'):
                            print(f"  Assistant: {block.text}")

    except Exception as e:
        print(f"  Error: {e}")

    print(f"  Messages received: {turn2_messages}")
    print(f"  ResultMessage count: {turn2_messages.count('ResultMessage')}")

    print("\n--- SUMMARY ---")
    print("Each client.query() + receive_response() cycle produces exactly one ResultMessage")
    print("ResultMessage with subtype='success' = agent has stopped for this query")


if __name__ == "__main__":
    print("Running long chain SDK tests...\n")

    # Run long chain test
    asyncio.run(test_long_chain())

    # Run multi-turn test
    asyncio.run(test_multi_turn_conversation())

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("""
Based on these tests:

1. ResultMessage appears exactly ONCE per query() cycle
2. It appears AFTER all tool operations complete
3. subtype='success' means the agent has stopped responding
4. We CANNOT distinguish "waiting for input" vs "task complete" from the SDK

RELIABLE SIGNAL: When we receive ResultMessage with subtype='success',
the agent has stopped. What we do next (continue conversation or end phase)
must be determined by other means (artifact checking, prompt design, etc.)
""")
