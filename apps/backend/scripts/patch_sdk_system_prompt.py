#!/usr/bin/env python3
"""
Runtime monkey-patch to add CLAUDE_SYSTEM_PROMPT_FILE support to claude-agent-sdk.

This module provides a runtime patch for the SDK's subprocess_cli.py to support
reading system prompt from a file specified via CLAUDE_SYSTEM_PROMPT_FILE environment
variable.

This is a workaround for the lack of --system-prompt-file support in the SDK.
See: https://github.com/AndyMik90/Auto-Claude/issues/384

Usage:
    from scripts.patch_sdk_system_prompt import apply_sdk_patch
    apply_sdk_patch()
"""

import os
from pathlib import Path


def apply_sdk_patch():
    """
    Apply a runtime monkey-patch to the SDK's SubprocessCLITransport
    to support CLAUDE_SYSTEM_PROMPT_FILE environment variable.

    This patches both _build_command to remove system_prompt from args,
    and connect() to write it to stdin, avoiding ARG_MAX limits.
    """
    try:
        from claude_agent_sdk._internal.transport.subprocess_cli import (
            SubprocessCLITransport,
        )
    except ImportError:
        # SDK not available, skip patching
        return

    # Store original methods
    original_build_command = SubprocessCLITransport._build_command
    original_connect = SubprocessCLITransport.connect

    def patched_build_command(self) -> list[str]:
        """
        Patched version of _build_command that removes --system-prompt when
        CLAUDE_SYSTEM_PROMPT_FILE is set (to be sent via stdin instead).

        This avoids ARG_MAX limits by not passing large prompts as command-line args.
        """
        cmd = original_build_command(self)

        # Check if CLAUDE_SYSTEM_PROMPT_FILE environment variable is set
        system_prompt_file = os.environ.get("CLAUDE_SYSTEM_PROMPT_FILE")
        if system_prompt_file and Path(system_prompt_file).exists():
            # Remove --system-prompt argument from command to avoid ARG_MAX
            # The prompt will be sent via stdin in patched_connect instead
            new_cmd = []
            i = 0
            while i < len(cmd):
                if cmd[i] == "--system-prompt" and i + 1 < len(cmd):
                    # Skip both the flag and its value
                    i += 2
                else:
                    new_cmd.append(cmd[i])
                    i += 1
            cmd = new_cmd

        return cmd

    async def patched_connect(self):
        """
        Patched version of connect() that handles CLAUDE_SYSTEM_PROMPT_FILE.

        When CLAUDE_SYSTEM_PROMPT_FILE is set, reads the system prompt from that file
        and writes it to the subprocess stdin before any user messages, avoiding ARG_MAX limits.
        """
        # Check for CLAUDE_SYSTEM_PROMPT_FILE environment variable before starting
        system_prompt_file = os.environ.get("CLAUDE_SYSTEM_PROMPT_FILE")
        system_prompt_content = None

        if system_prompt_file and Path(system_prompt_file).exists():
            try:
                with open(system_prompt_file, encoding="utf-8") as f:
                    system_prompt_content = f.read()
                # Clear from environment so we don't process it again
                del os.environ["CLAUDE_SYSTEM_PROMPT_FILE"]
            except OSError as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Failed to read CLAUDE_SYSTEM_PROMPT_FILE {system_prompt_file}: {e}"
                )
                system_prompt_content = None

        # Call original connect to start the subprocess
        await original_connect(self)

        # If we have large system prompt content, write it to stdin first
        # This must be done before any user messages are sent
        if system_prompt_content and self._stdin_stream:
            try:
                # Write system prompt followed by a message separator
                # The SDK uses SSE format, so we need to send it as a message
                # Format: event: message\ndata: <json>\n\n
                import json

                message_data = {
                    "type": "message",
                    "message": {"role": "system", "content": system_prompt_content},
                }

                await self._stdin_stream.send(
                    f"event: message\ndata: {json.dumps(message_data)}\n\n"
                )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Failed to write system prompt to subprocess stdin: {e}")

    # Apply the monkey-patches
    SubprocessCLITransport._build_command = patched_build_command
    SubprocessCLITransport.connect = patched_connect


# Auto-apply patch on import
apply_sdk_patch()
