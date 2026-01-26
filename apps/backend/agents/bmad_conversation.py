"""
BMAD Two-Agent Conversation Loop

This module implements the conversation pattern between:
- BMAD Agent: Runs the BMAD methodology workflows
- Human Replacement Agent: Responds to BMAD's questions as a knowledgeable collaborator

COMPLETION DETECTION STRATEGY:
Instead of fragile pattern matching, we use STRUCTURAL COMPLETION CHECKING:
- Each phase has expected artifacts (e.g., tech_spec → tech-spec.md)
- After each BMAD turn (ResultMessage.subtype = "success"), we check if artifact exists
- If artifact exists and has content → phase complete
- If no artifact → assume waiting for input, invoke Human Replacement

This is reliable because we check for actual deliverables, not text patterns.
The SDK gives us a reliable "agent has stopped" signal (ResultMessage), and
artifact checking tells us if the work is done.
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from apps.backend.core.client import create_client
from apps.backend.core.debug import (
    debug,
    debug_error,
    debug_section,
    debug_success,
    debug_warning,
)
from apps.backend.task_logger import LogPhase, get_task_logger


# =============================================================================
# PHASE TYPE CLASSIFICATION
# =============================================================================
# Phases are classified into two categories with different completion strategies:
#
# 1. DOCUMENTATION PHASES: Produce a single artifact at the end
#    - Completion signal: Artifact exists with content
#    - Questions: Only happen BEFORE artifact is created
#    - Examples: tech_spec, prd, architecture, epics
#
# 2. IMPLEMENTATION PHASES: Produce code changes over multiple turns
#    - Completion signal: Agent explicitly says "done" (no artifact to check)
#    - Questions: Can happen MID-DEVELOPMENT (critical!)
#    - Examples: quick_dev, dev, review
#
# For implementation phases, we ALWAYS invoke Human Replacement after each turn
# because BMAD is known for discovering gaps mid-implementation and asking:
# - "The tech spec says X but I found Y. Should I...?"
# - "I discovered an edge case not in the epic. How should I handle it?"
# - "The API doesn't exist. Create it or use alternative?"

# Phases that produce a checkable artifact
DOCUMENTATION_PHASES: set[str] = {
    "tech_spec",
    "analyze",
    "prd",
    "architecture",
    "epics",
    "stories",
    "security",
    "devops",
}

# Phases where questions can arise mid-way (always invoke Human Replacement)
IMPLEMENTATION_PHASES: set[str] = {
    "quick_dev",
    "dev",
    "review",
}

# Expected artifacts for DOCUMENTATION phases only
# These are used to determine if a documentation phase is complete
PHASE_ARTIFACTS: dict[str, list[str]] = {
    # Quick Flow phases
    "tech_spec": [
        "planning-artifacts/tech-spec.md",
        "tech-spec.md",
    ],
    # BMad Method phases
    "analyze": [
        "project-context.md",
        "project-scan-report.json",
    ],
    "prd": [
        "planning-artifacts/prd.md",
        "prd.md",
    ],
    "architecture": [
        "planning-artifacts/architecture.md",
        "architecture.md",
    ],
    "epics": [
        "planning-artifacts/epics/",  # Directory with epics
        "planning-artifacts/epic-",  # Any epic file
        "epics/",
    ],
    "stories": [
        "implementation-artifacts/sprint-status.yaml",
        "sprint-status.yaml",
    ],
    # Enterprise phases
    "security": [
        "planning-artifacts/security.md",
        "security.md",
    ],
    "devops": [
        "planning-artifacts/devops.md",
        "devops.md",
    ],
    # NOTE: quick_dev, dev, review are NOT here - they don't have artifacts
}

# Minimum file size to consider an artifact "complete" (not just created empty)
MIN_ARTIFACT_SIZE = 100  # bytes


def check_phase_artifacts(spec_dir: Path, phase: str) -> tuple[bool, str | None]:
    """Check if expected artifacts for a phase exist and have content.

    This is the PRIMARY mechanism for determining if a phase is complete.
    We check for actual deliverables rather than parsing text output.

    Args:
        spec_dir: Spec directory containing _bmad-output/
        phase: BMAD phase name

    Returns:
        Tuple of (is_complete, artifact_path_if_found)
    """
    artifacts = PHASE_ARTIFACTS.get(phase, [])
    if not artifacts:
        # Unknown phase - can't verify structurally
        debug(
            "bmad.artifacts",
            f"No artifacts defined for phase '{phase}' - using fallback detection",
        )
        return False, None

    bmad_output = spec_dir / "_bmad-output"

    for artifact_path in artifacts:
        full_path = bmad_output / artifact_path

        # Check for directory (e.g., "epics/")
        if artifact_path.endswith("/"):
            if full_path.exists() and full_path.is_dir():
                # Check if directory has any files
                files = list(full_path.iterdir())
                if files:
                    debug(
                        "bmad.artifacts",
                        f"Found artifact directory with {len(files)} files: {artifact_path}",
                    )
                    return True, str(full_path)

        # Check for file pattern (e.g., "epic-" matches any file starting with epic-)
        elif not artifact_path.endswith(".md") and not artifact_path.endswith(
            ".json"
        ) and not artifact_path.endswith(".yaml"):
            # This is a prefix pattern - search for matching files
            parent = full_path.parent
            prefix = full_path.name
            if parent.exists():
                for f in parent.iterdir():
                    if f.name.startswith(prefix) and f.stat().st_size >= MIN_ARTIFACT_SIZE:
                        debug(
                            "bmad.artifacts",
                            f"Found artifact matching pattern '{artifact_path}': {f.name}",
                        )
                        return True, str(f)

        # Check for specific file
        else:
            if full_path.exists() and full_path.is_file():
                size = full_path.stat().st_size
                if size >= MIN_ARTIFACT_SIZE:
                    debug(
                        "bmad.artifacts",
                        f"Found artifact: {artifact_path} ({size} bytes)",
                    )
                    return True, str(full_path)
                else:
                    debug(
                        "bmad.artifacts",
                        f"Artifact exists but too small ({size} bytes): {artifact_path}",
                    )

    debug(
        "bmad.artifacts",
        f"No artifacts found for phase '{phase}'",
        checked_paths=[str(bmad_output / p) for p in artifacts],
    )
    return False, None


def is_phase_structurally_complete(spec_dir: Path, phase: str) -> bool:
    """Check if a phase is complete based on artifact existence.

    This is the RELIABLE completion signal - we check if the expected
    deliverable exists rather than parsing text output.

    Args:
        spec_dir: Spec directory
        phase: BMAD phase name

    Returns:
        True if phase artifact exists and has content
    """
    is_complete, artifact_path = check_phase_artifacts(spec_dir, phase)

    if is_complete:
        debug_success(
            "bmad.artifacts",
            f"Phase '{phase}' structurally complete",
            artifact=artifact_path,
        )
    else:
        debug(
            "bmad.artifacts",
            f"Phase '{phase}' NOT structurally complete - no artifact found",
        )

    return is_complete


def _get_tool_detail(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Extract meaningful detail from tool input for user-friendly logging.

    Instead of "Using tool: Read", show "Reading sdk_utils.py"
    Instead of "Using tool: Grep", show "Searching for 'pattern'"
    """
    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path:
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            return f"📖 Reading {filename}"
        return "📖 Reading file"

    if tool_name == "Grep":
        pattern = tool_input.get("pattern", "")
        if pattern:
            pattern_preview = pattern[:40] + "..." if len(pattern) > 40 else pattern
            return f"🔍 Searching for '{pattern_preview}'"
        return "🔍 Searching codebase"

    if tool_name == "Glob":
        pattern = tool_input.get("pattern", "")
        if pattern:
            return f"📁 Finding files matching '{pattern}'"
        return "📁 Finding files"

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            cmd_preview = command[:50] + "..." if len(command) > 50 else command
            return f"⚡ Running: {cmd_preview}"
        return "⚡ Running command"

    if tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        if file_path:
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            return f"✏️ Editing {filename}"
        return "✏️ Editing file"

    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if file_path:
            filename = file_path.split("/")[-1] if "/" in file_path else file_path
            return f"📝 Writing {filename}"
        return "📝 Writing file"

    if tool_name == "Task":
        agent_type = tool_input.get("subagent_type", "unknown")
        return f"🤖 Spawning agent: {agent_type}"

    if tool_name == "WebSearch":
        query = tool_input.get("query", "")
        if query:
            query_preview = query[:40] + "..." if len(query) > 40 else query
            return f"🌐 Web search: '{query_preview}'"
        return "🌐 Web search"

    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        if url:
            url_preview = url[:50] + "..." if len(url) > 50 else url
            return f"🌐 Fetching: {url_preview}"
        return "🌐 Fetching URL"

    # MCP tools
    if tool_name.startswith("mcp__"):
        # Extract readable name from mcp__server__tool format
        parts = tool_name.split("__")
        if len(parts) >= 3:
            server = parts[1]
            tool = parts[2]
            return f"🔌 MCP {server}: {tool}"
        return f"🔌 MCP: {tool_name}"

    # Default fallback
    return f"🔧 Using tool: {tool_name}"


def _get_tool_input_display(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Extract a brief tool input description for task_logger display.

    Returns a concise string suitable for the frontend log display.
    """
    if not tool_input:
        return None

    if tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path:
            # Show just filename or last part of path
            if len(file_path) > 50:
                return "..." + file_path[-47:]
            return file_path
        return None

    if tool_name in ("Grep", "Glob"):
        pattern = tool_input.get("pattern", "")
        if pattern:
            if len(pattern) > 50:
                return f"pattern: {pattern[:47]}..."
            return f"pattern: {pattern}"
        return None

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if command:
            if len(command) > 50:
                return command[:47] + "..."
            return command
        return None

    if tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "")
        if file_path:
            if len(file_path) > 50:
                return "..." + file_path[-47:]
            return file_path
        return None

    if tool_name == "Task":
        agent_type = tool_input.get("subagent_type", "")
        description = tool_input.get("description", "")
        if agent_type:
            return (
                f"{agent_type}: {description[:30]}..."
                if len(description) > 30
                else f"{agent_type}: {description}"
            )
        return None

    # For MCP and other tools, show first available string value
    for key in ["url", "query", "path", "file_path", "pattern", "command"]:
        if key in tool_input:
            val = str(tool_input[key])
            if len(val) > 50:
                return f"{key}: {val[:47]}..."
            return f"{key}: {val}"

    return None


# Patterns that indicate the phase is complete (these are the ONLY patterns we need)
# We use an "assume waiting" approach: if the agent's turn ends with text-only
# (no pending tool calls), we assume it's waiting for input UNLESS it matches
# a completion pattern. This is more robust than trying to match all question formats.
COMPLETION_PATTERNS = [
    # Explicit completion signals
    r"workflow complete",
    r"phase complete",
    r"documentation.*complete",
    r"successfully.*created",
    r"finished.*step\s*11",  # PRD final step
    r"all.*steps.*complete",
    r"implementation.*complete",
    r"review.*complete",
    r"code review.*complete",
    # File creation confirmations that indicate done (not waiting)
    r"created.*\.md",
    r"saved.*to.*\.md",
    r"written.*to.*file",
    # Explicit "I'm done" signals
    r"task.*complete",
    r"done.*implementing",
    r"finished.*implementation",
    r"completed.*successfully",
    # Summary/report endings (indicating wrap-up, not questions)
    r"summary.*above",
    r"report.*generated",
    r"findings.*documented",
]

# Patterns that indicate the agent is DEFINITELY waiting for input
# Used as a positive signal in addition to the structural detection
INPUT_SIGNAL_PATTERNS = [
    # Menu/choice patterns - Quick Flow style (multi-line, so use [\s\S] instead of .)
    r"\[C\]\s*Continue",
    r"\[1\][\s\S]*?\[2\]",  # Numbered options (multi-line safe)
    r"\[P\][\s\S]*?\[W\]",  # Quick Flow: [P]roceed, [W]ait (multi-line safe)
    r"\[P\][\s\S]*?\[E\]",  # Quick Flow: [P]roceed, [E]xit (multi-line safe)
    r"\[W\][\s\S]*?\[E\]",  # Quick Flow: [W]ait, [E]xit (multi-line safe)
    r"Your choice",
    r"Select.*option",
    r"Choose.*option",
    r"Pick.*:",
    # Quick Flow explicit markers
    r"\[P\]\s*Proceed",
    r"\[W\]\s*Wait",
    r"\[E\]\s*Exit",
    # Direct question indicators - common question starters
    r"\(y/n\)",
    r"\(yes/no\)",
    r"What's your",
    r"What do you",
    r"What is your",
    r"Should we",
    r"Should this",
    r"Would you like",
    r"Do you want",
    r"Do you have",
    r"How should",
    r"How would",
    r"Which.*prefer",
    r"Let me know",
    r"Can you (tell|clarify|confirm|specify)",
    # Waiting/response indicators
    r"waiting for.*input",
    r"waiting for.*response",
    r"need.*response",
    r"your.*decision",
    r"your.*preference",
    r"your.*input",
    r"your.*feedback",
    # BMAD conversation markers
    r"Ready to proceed\?",
    r"Shall I continue\?",
    r"Would you like me to",
    r"Please (confirm|choose|select|pick|answer|respond|provide|share)",
    # Technical question patterns (Barry's style)
    r"\*\*\d+\.\s+.*:\*\*",  # Numbered bold headers like "**1. Platform:**"
    r"##.*Questions",  # Markdown headers with "Questions"
    r"questions.*for you",
    r"answer.*questions",
    r"specific.*questions",
]


def is_phase_complete(text: str) -> bool:
    """Check if the BMAD workflow indicates phase completion.

    Args:
        text: The BMAD agent's output text

    Returns:
        True if the phase appears to be complete
    """
    for pattern in COMPLETION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return True

    return False


def has_input_signal(text: str) -> bool:
    """Check if text contains explicit signals that input is expected.

    This is used in addition to structural detection to boost confidence
    that we should invoke the Human Replacement agent.

    Args:
        text: The BMAD agent's output text

    Returns:
        True if explicit input signals are detected
    """
    for pattern in INPUT_SIGNAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
            return True
    return False


def is_waiting_for_input(text: str, ended_with_text_only: bool = True) -> bool:
    """Check if the BMAD agent output indicates it's waiting for input.

    Uses a robust "assume waiting" approach:
    1. If the turn ended with tool calls pending, NOT waiting
    2. If the turn ended with text-only AND matches completion patterns, DONE
    3. Otherwise, assume waiting for input

    This inverts the fragile pattern-matching approach. Instead of trying
    to match all possible question formats (impossible), we only need to
    detect when the agent is DONE.

    Args:
        text: The BMAD agent's output text
        ended_with_text_only: True if the agent's turn ended with text only
                              (no pending tool calls). This is the structural signal.

    Returns:
        True if the agent appears to be waiting for human input
    """
    # If there are pending tool calls, agent is processing, not waiting
    if not ended_with_text_only:
        return False

    # Check for completion patterns first
    if is_phase_complete(text):
        return False

    # Check for explicit input signals (high confidence)
    if has_input_signal(text):
        return True

    # Heuristic: if text ends with a question mark, likely waiting
    text_stripped = text.strip()
    if text_stripped.endswith("?"):
        return True

    # Heuristic: if text is short and doesn't look like completion, assume waiting
    # Long outputs with file contents are more likely to be "done" outputs
    if len(text_stripped) < 500:
        return True

    # For longer outputs, check if they look like they're asking something
    # Look at the last portion (expanded to 1500 chars to catch more context)
    last_portion = text_stripped[-1500:]

    # Check for input signals in the last portion
    if has_input_signal(last_portion):
        return True

    # Count question marks in the last portion - multiple questions = likely waiting
    question_count = last_portion.count("?")
    if question_count >= 2:
        # Multiple questions in the last portion strongly suggests waiting for answers
        return True

    # Single question mark at the end of last portion
    if last_portion.strip().endswith("?"):
        return True

    # Check if last portion contains common question phrases (case-insensitive)
    question_phrases = [
        "what do you think",
        "what's your",
        "which option",
        "please answer",
        "please respond",
        "let me know",
        "your preference",
        "your choice",
        "any preference",
        "any questions",
    ]
    last_portion_lower = last_portion.lower()
    for phrase in question_phrases:
        if phrase in last_portion_lower:
            return True

    # Default: for long outputs without signals, assume complete
    return False


def extract_question_context(text: str, max_chars: int = 2000) -> str:
    """Extract the relevant question/decision context from BMAD output.

    Takes the last portion of the output that contains the question or menu,
    providing enough context for the Human Replacement agent to respond.

    Args:
        text: Full BMAD agent output
        max_chars: Maximum characters to include

    Returns:
        The relevant context for the Human Replacement agent
    """
    # Get the last max_chars, but try to start at a paragraph boundary
    if len(text) <= max_chars:
        return text

    truncated = text[-max_chars:]

    # Try to find a good starting point (paragraph break)
    paragraph_break = truncated.find("\n\n")
    if paragraph_break > 0 and paragraph_break < max_chars // 2:
        truncated = truncated[paragraph_break + 2 :]

    return truncated


def load_human_replacement_prompt(
    phase: str,
    task_description: str,
    project_context: str,
    bmad_message: str,
) -> str:
    """Load and populate the Human Replacement agent prompt for a phase.

    Args:
        phase: BMAD phase (analyze, prd, architecture, epics, dev, review)
        task_description: The original task description
        project_context: Context about the project
        bmad_message: The BMAD agent's message requiring response

    Returns:
        The populated prompt for the Human Replacement agent
    """
    # Map phase to prompt file
    phase_prompt_map = {
        # BMad Method phases
        "analyze": "bmad_human_analyze.md",
        "prd": "bmad_human_prd.md",
        "architecture": "bmad_human_architecture.md",
        "epics": "bmad_human_epics.md",
        "stories": "bmad_human_epics.md",  # Same as epics
        "dev": "bmad_human_dev.md",
        "review": "bmad_human_review.md",
        # Quick Flow phases (Barry agent)
        "tech_spec": "bmad_human_dev.md",  # Tech spec uses dev persona
        "quick_dev": "bmad_human_dev.md",  # Quick dev uses dev persona
    }

    prompt_file = phase_prompt_map.get(phase, "bmad_human_base.md")

    # Load the prompt template
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_path = prompts_dir / prompt_file

    # Fall back to base prompt if phase-specific doesn't exist
    if not prompt_path.exists():
        prompt_path = prompts_dir / "bmad_human_base.md"

    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Substitute placeholders
    prompt = prompt_template.replace(
        "{task_description}", task_description or "No task description provided"
    )
    prompt = prompt.replace(
        "{project_context}", project_context or "No additional project context"
    )
    prompt = prompt.replace("{bmad_message}", bmad_message)

    return prompt


async def run_human_replacement_response(
    project_dir: Path,
    spec_dir: Path,
    phase: str,
    task_description: str,
    project_context: str,
    bmad_message: str,
    model: str = "claude-sonnet-4-5-20250929",
) -> str:
    """Run the Human Replacement agent to generate a response to BMAD.

    The Human Replacement agent gives SHORT, DECISIVE responses - typically
    just "C" for continue, "y" for yes, or brief one-line answers.

    Args:
        project_dir: Project directory path
        spec_dir: Spec directory path
        phase: Current BMAD phase
        task_description: Original task description
        project_context: Project context information
        bmad_message: The BMAD agent's message requiring response
        model: Model to use for the Human Replacement agent (ignored, uses Haiku)

    Returns:
        The Human Replacement agent's response
    """
    debug_section("bmad.human_replacement", f"GENERATING RESPONSE FOR {phase.upper()}")

    # Load the appropriate prompt
    prompt = load_human_replacement_prompt(
        phase=phase,
        task_description=task_description,
        project_context=project_context,
        bmad_message=bmad_message,
    )

    debug(
        "bmad.human_replacement",
        "Prompt prepared",
        phase=phase,
        prompt_length=len(prompt),
        bmad_message_preview=bmad_message[:200] + "..."
        if len(bmad_message) > 200
        else bmad_message,
    )

    # Create a lightweight client for the Human Replacement agent
    # Use Haiku for speed - we just need short, decisive responses
    # CRITICAL: Uses "human_replacement" agent type which has NO tools at all
    # This agent can ONLY respond with text - no file operations, no bash, nothing
    client = create_client(
        project_dir,
        spec_dir,
        model="claude-haiku-4-5-20251001",  # Fast model for short responses
        agent_type="human_replacement",  # NO tools - response-only agent
        max_thinking_tokens=None,  # No extended thinking - just respond
    )

    try:
        async with client:
            # Send the prompt and get response
            await client.query(prompt)

            response_text = ""
            msg_count = 0

            debug("bmad.human", "🤖 Human Replacement agent processing...")

            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                msg_count += 1

                # Log thinking (Haiku rarely uses extended thinking, but just in case)
                if msg_type == "ThinkingBlock" or (
                    hasattr(msg, "type") and msg.type == "thinking"
                ):
                    thinking_text = getattr(msg, "thinking", "") or getattr(
                        msg, "text", ""
                    )
                    if thinking_text:
                        debug("bmad.human", f"🧠 Thinking ({len(thinking_text)} chars)")

                # Collect text
                if hasattr(msg, "content"):
                    for block in msg.content:
                        if hasattr(block, "text"):
                            response_text += block.text

            # Clean up response - remove any meta-commentary
            response_text = response_text.strip()

            debug_success(
                "bmad.human",
                "Response generated",
                messages=msg_count,
                response=response_text[:100] + "..."
                if len(response_text) > 100
                else response_text,
            )

            return response_text

    except Exception as e:
        debug_error("bmad.human", f"Failed to generate response: {e}")
        # Return a safe default response
        return "Continue"


async def run_bmad_conversation_loop(
    project_dir: Path,
    spec_dir: Path,
    phase: str,
    workflow_prompt: str,
    task_description: str,
    project_context: str = "",
    model: str = "claude-sonnet-4-5-20250929",
    max_turns: int = 20,
    progress_callback: Callable[[str, float], None] | None = None,
) -> tuple[str, str]:
    """Run the BMAD workflow with Human Replacement agent responses.

    This implements the two-agent conversation loop:
    1. BMAD agent runs and may ask questions
    2. Human Replacement agent responds to questions
    3. Loop continues until phase complete or max turns reached

    Args:
        project_dir: Project directory path
        spec_dir: Spec directory path
        phase: Current BMAD phase
        workflow_prompt: The BMAD workflow instructions
        task_description: Original task description
        project_context: Project context information
        model: Model to use for agents
        max_turns: Maximum conversation turns before stopping
        progress_callback: Optional callback for progress updates

    Returns:
        Tuple of (status, full_conversation_text)
    """
    debug_section("bmad.conversation", f"STARTING CONVERSATION LOOP - {phase.upper()}")

    # Get task logger for structured frontend logging
    task_logger = get_task_logger(spec_dir)

    # Map BMAD phase to LogPhase
    log_phase_map = {
        # BMad Method phases
        "analyze": LogPhase.PLANNING,
        "prd": LogPhase.PLANNING,
        "architecture": LogPhase.PLANNING,
        "epics": LogPhase.PLANNING,
        "stories": LogPhase.PLANNING,
        "dev": LogPhase.CODING,
        "review": LogPhase.VALIDATION,
        # Quick Flow phases
        "tech_spec": LogPhase.PLANNING,
        "quick_dev": LogPhase.CODING,
    }
    log_phase = log_phase_map.get(phase, LogPhase.CODING)

    # Debug: log the phase mapping for tracing
    debug(
        "bmad.conversation",
        "Phase mapping",
        input_phase=phase,
        log_phase=log_phase.value,
        found_in_map=phase in log_phase_map,
    )

    # Start the phase in task_logger for proper phase tracking
    task_logger.start_phase(log_phase, f"Starting BMAD {phase} phase")

    conversation_history = []
    full_response = ""
    turn_count = 0

    # Start with the workflow prompt
    current_prompt = workflow_prompt

    while turn_count < max_turns:
        turn_count += 1

        debug(
            "bmad.conversation",
            f"Turn {turn_count}/{max_turns}",
            phase=phase,
            prompt_length=len(current_prompt),
        )

        if progress_callback:
            progress = 30 + (turn_count / max_turns) * 60  # Progress from 30% to 90%
            progress_callback(f"BMAD conversation turn {turn_count}", progress)

        # Create BMAD client
        bmad_client = create_client(
            project_dir,
            spec_dir,
            model=model,
            agent_type="coder",
            max_thinking_tokens=None,
        )

        try:
            # Run BMAD agent
            async with bmad_client:
                await bmad_client.query(current_prompt)

                bmad_response = ""
                msg_count = 0
                tool_calls = 0
                subagent_tool_ids: dict[str, str] = {}  # tool_id -> agent_name
                pending_tools: dict[
                    str, str
                ] = {}  # tool_id -> tool_name for tool_end matching
                received_result_message = False  # Track if SDK signals completion
                result_message_subtype = None  # Track the subtype if any

                debug("bmad.agent", "Agent session started, processing stream...")

                async for msg in bmad_client.receive_response():
                    msg_type = type(msg).__name__
                    msg_count += 1

                    # Log thinking blocks
                    if msg_type == "ThinkingBlock" or (
                        hasattr(msg, "type") and msg.type == "thinking"
                    ):
                        thinking_text = getattr(msg, "thinking", "") or getattr(
                            msg, "text", ""
                        )
                        if thinking_text:
                            debug(
                                "bmad.agent",
                                f"🧠 AI thinking ({len(thinking_text)} chars)",
                                preview=thinking_text[:150].replace("\n", " ") + "...",
                            )

                    # Log tool use blocks
                    if msg_type == "ToolUseBlock" or (
                        hasattr(msg, "type") and msg.type == "tool_use"
                    ):
                        tool_name = getattr(msg, "name", "")
                        tool_id = getattr(msg, "id", "unknown")
                        tool_input = getattr(msg, "input", {})
                        tool_calls += 1

                        # Track tool for result matching
                        pending_tools[tool_id] = tool_name

                        # Track subagent invocations
                        if tool_name == "Task":
                            agent_name = tool_input.get("subagent_type", "unknown")
                            subagent_tool_ids[tool_id] = agent_name

                        # Get human-readable tool input for display
                        tool_input_display = _get_tool_input_display(
                            tool_name, tool_input
                        )

                        # Log via task_logger for frontend display
                        task_logger.tool_start(
                            tool_name,
                            tool_input_display,
                            log_phase,
                            print_to_console=True,
                        )

                        # Also debug log
                        tool_detail = _get_tool_detail(tool_name, tool_input)
                        debug("bmad.agent", tool_detail)

                    # Log tool results
                    if msg_type == "ToolResultBlock" or (
                        hasattr(msg, "type") and msg.type == "tool_result"
                    ):
                        tool_id = getattr(msg, "tool_use_id", "unknown")
                        is_error = getattr(msg, "is_error", False)
                        result_content = getattr(msg, "content", "")

                        # Handle list of content blocks
                        if isinstance(result_content, list):
                            result_content = " ".join(
                                str(getattr(c, "text", c)) for c in result_content
                            )

                        # Get tool name from pending tools
                        tool_name = pending_tools.pop(tool_id, "unknown")
                        result_preview = (
                            str(result_content)[:200].replace("\n", " ").strip()
                        )

                        # Log via task_logger for frontend display
                        task_logger.tool_end(
                            tool_name,
                            success=not is_error,
                            result=result_preview if result_preview else None,
                            detail=str(result_content)
                            if len(str(result_content)) > 200
                            else None,
                            phase=log_phase,
                            print_to_console=False,
                        )

                        if tool_id in subagent_tool_ids:
                            agent_name = subagent_tool_ids[tool_id]
                            status = "❌ ERROR" if is_error else "✅ Complete"
                            debug(
                                "bmad.agent",
                                f"Agent {agent_name} {status}",
                                result=result_preview
                                + ("..." if len(str(result_content)) > 200 else ""),
                            )
                        elif is_error:
                            debug_warning("bmad.agent", f"Tool error: {result_preview}")

                    # Collect text output from AssistantMessage
                    if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__

                            # Check for tool use blocks within content
                            if (
                                block_type == "ToolUseBlock"
                                or getattr(block, "type", "") == "tool_use"
                            ):
                                tool_name = getattr(block, "name", "")
                                tool_id = getattr(block, "id", "unknown")
                                tool_input = getattr(block, "input", {})
                                tool_calls += 1

                                # Track tool for result matching
                                if tool_id not in pending_tools:
                                    pending_tools[tool_id] = tool_name

                                if tool_name == "Task":
                                    agent_name = tool_input.get(
                                        "subagent_type", "unknown"
                                    )
                                    if tool_id not in subagent_tool_ids:
                                        subagent_tool_ids[tool_id] = agent_name

                                # Get human-readable tool input for display
                                tool_input_display = _get_tool_input_display(
                                    tool_name, tool_input
                                )

                                # Log via task_logger for frontend display
                                task_logger.tool_start(
                                    tool_name,
                                    tool_input_display,
                                    log_phase,
                                    print_to_console=True,
                                )

                                tool_detail = _get_tool_detail(tool_name, tool_input)
                                debug("bmad.agent", tool_detail)

                            # Collect text
                            if block_type == "TextBlock" and hasattr(block, "text"):
                                bmad_response += block.text
                                print(block.text, end="", flush=True)
                                # Log text to task logger
                                if block.text.strip():
                                    task_logger.log(
                                        block.text,
                                        phase=log_phase,
                                        print_to_console=False,
                                    )

                    # Handle ResultMessage - SDK-level completion signal
                    # This is similar to TypeScript SDK's system.subtype === 'completion'
                    if msg_type == "ResultMessage" or (
                        hasattr(msg, "type") and msg.type == "result"
                    ):
                        received_result_message = True
                        result_message_subtype = getattr(msg, "subtype", None)
                        debug(
                            "bmad.agent",
                            f"📌 ResultMessage received",
                            subtype=result_message_subtype,
                            cost=getattr(msg, "total_cost_usd", None),
                            duration=getattr(msg, "duration_ms", None),
                        )

                    # Handle UserMessage with tool results (subagent results)
                    if msg_type == "UserMessage" and hasattr(msg, "content"):
                        for block in msg.content:
                            block_type = type(block).__name__
                            if (
                                block_type == "ToolResultBlock"
                                or getattr(block, "type", "") == "tool_result"
                            ):
                                tool_id = getattr(block, "tool_use_id", "unknown")
                                is_error = getattr(block, "is_error", False)
                                result_content = getattr(block, "content", "")

                                if isinstance(result_content, list):
                                    result_content = " ".join(
                                        str(getattr(c, "text", c))
                                        for c in result_content
                                    )

                                # Get tool name from pending tools
                                tool_name = pending_tools.pop(tool_id, "unknown")
                                result_preview = (
                                    str(result_content)[:200].replace("\n", " ").strip()
                                )

                                # Log via task_logger for frontend display
                                task_logger.tool_end(
                                    tool_name,
                                    success=not is_error,
                                    result=result_preview if result_preview else None,
                                    phase=log_phase,
                                    print_to_console=False,
                                )

                                if tool_id in subagent_tool_ids:
                                    agent_name = subagent_tool_ids[tool_id]
                                    status = "❌ ERROR" if is_error else "✅ Complete"
                                    debug(
                                        "bmad.agent",
                                        f"Agent {agent_name} {status}",
                                        result=result_preview
                                        + (
                                            "..."
                                            if len(str(result_content)) > 200
                                            else ""
                                        ),
                                    )

                full_response += bmad_response + "\n"
                conversation_history.append({"role": "bmad", "content": bmad_response})

                # Structural signal: did the turn end with text-only (no pending tools)?
                ended_with_text_only = len(pending_tools) == 0

                debug_success(
                    "bmad.agent",
                    f"Turn {turn_count} complete",
                    messages=msg_count,
                    tool_calls=tool_calls,
                    response_length=len(bmad_response),
                    ended_with_text_only=ended_with_text_only,
                    pending_tools=len(pending_tools),
                    received_result_message=received_result_message,
                    result_subtype=result_message_subtype,
                )

                # =============================================================
                # PHASE-TYPE-SPECIFIC COMPLETION DETECTION
                # =============================================================
                # Different strategies for documentation vs implementation phases:
                #
                # DOCUMENTATION PHASES: Check for artifact, then invoke Human
                # IMPLEMENTATION PHASES: Always invoke Human (questions mid-way!)

                is_implementation_phase = phase in IMPLEMENTATION_PHASES
                is_documentation_phase = phase in DOCUMENTATION_PHASES

                debug(
                    "bmad.conversation",
                    "Determining completion strategy",
                    phase=phase,
                    is_implementation_phase=is_implementation_phase,
                    is_documentation_phase=is_documentation_phase,
                )

                # =============================================================
                # DOCUMENTATION PHASES: Artifact-based completion
                # =============================================================
                if is_documentation_phase:
                    # Check if the expected artifact exists
                    if is_phase_structurally_complete(spec_dir, phase):
                        debug_success(
                            "bmad.conversation",
                            "Documentation phase COMPLETE - artifact found",
                            phase=phase,
                        )
                        task_logger.end_phase(log_phase, success=True)
                        return "complete", full_response

                    # No artifact yet - agent must be asking questions
                    debug(
                        "bmad.conversation",
                        "Documentation phase: No artifact yet, invoking Human Replacement",
                        phase=phase,
                    )

                # =============================================================
                # IMPLEMENTATION PHASES: Always invoke Human Replacement
                # =============================================================
                # BMAD can ask questions MID-DEVELOPMENT:
                # - "Found edge case not in spec, how to handle?"
                # - "API doesn't exist, should I create it?"
                # - "Existing code conflicts with spec, refactor or adapt?"
                #
                # We ALWAYS invoke Human Replacement and let it decide:
                # - If it's a question → Answer it
                # - If it's a status update → "Continue"
                # - If it's completion → "Looks good"
                if is_implementation_phase:
                    # Check for explicit completion patterns first
                    if is_phase_complete(bmad_response):
                        debug_success(
                            "bmad.conversation",
                            "Implementation phase COMPLETE - completion pattern detected",
                            phase=phase,
                        )
                        task_logger.end_phase(log_phase, success=True)
                        return "complete", full_response

                    debug(
                        "bmad.conversation",
                        "Implementation phase: Always invoking Human Replacement",
                        phase=phase,
                        reason="Implementation phases can have mid-development questions",
                    )

                # =============================================================
                # INVOKE HUMAN REPLACEMENT
                # =============================================================
                # At this point, we're invoking Human Replacement because:
                # - Documentation phase: No artifact found (must be asking questions)
                # - Implementation phase: Always invoke (questions can happen mid-way)

                # Extract the relevant context for the Human Replacement
                question_context = extract_question_context(bmad_response)

                # Log that Human Replacement is being invoked
                if task_logger:
                    # Use log_with_detail for expandable full content
                    question_preview = (
                        question_context[:150] + "..."
                        if len(question_context) > 150
                        else question_context
                    )
                    task_logger.log_with_detail(
                        content=f"[BMAD Agent] Message: {question_preview}",
                        detail=question_context,
                        phase=log_phase,
                        subphase="BMAD CONVERSATION",
                        collapsed=True,
                    )
                    task_logger.log(
                        "[Human Replacement Agent] Processing response...",
                        phase=log_phase,
                    )

                # Get Human Replacement response
                human_response = await run_human_replacement_response(
                    project_dir=project_dir,
                    spec_dir=spec_dir,
                    phase=phase,
                    task_description=task_description,
                    project_context=project_context,
                    bmad_message=question_context,
                    model=model,
                )

                conversation_history.append(
                    {"role": "human", "content": human_response}
                )
                full_response += f"\n[Human Response]: {human_response}\n\n"

                # Log to task_logger for frontend display with expandable detail
                if task_logger:
                    # Format the human response for clean frontend display
                    response_preview = (
                        human_response[:200] + "..."
                        if len(human_response) > 200
                        else human_response
                    )
                    task_logger.log_with_detail(
                        content=f"[Human Replacement Agent] Response: {response_preview}",
                        detail=human_response,
                        phase=log_phase,
                        subphase="BMAD CONVERSATION",
                        collapsed=True,
                    )

                print(f"\n[Human Response]: {human_response}\n")

                # Build context for next turn
                # Include the BMAD message and human response
                current_prompt = f"""
Continue the workflow. The previous exchange was:

BMAD Agent: {question_context}

Human Response: {human_response}

Please continue with the next step of the workflow based on this response.
"""
                # Loop continues - next iteration will check for artifact/completion again

        except Exception as e:
            debug_error("bmad.conversation", f"Error in conversation turn: {e}")
            task_logger.end_phase(log_phase, success=False, message=f"Error: {e}")
            return "error", full_response

    debug("bmad.conversation", f"Max turns ({max_turns}) reached")
    task_logger.end_phase(log_phase, success=True, message="Max turns reached")
    return "max_turns", full_response
