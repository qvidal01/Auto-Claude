#!/usr/bin/env python3
"""
ac-phase — Interactive phased spec executor for Auto-Claude
============================================================

Run from any repo with .auto-claude/specs/ to execute specs in
dependency-aware phases with review gates between them.

Usage:
    ac-phase                  # Interactive menu (auto-detects project)
    ac-phase --status         # Show phase & spec status
    ac-phase --run            # Run next pending phase
    ac-phase --run --phase 2  # Run specific phase
    ac-phase --run --all      # Run all phases (pause between each)
    ac-phase --run --no-pause # Run all without pausing
    ac-phase --init           # Auto-generate phases.json from specs
    ac-phase --edit           # Open phases.json for manual editing
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Graceful exit on Ctrl+C
# ---------------------------------------------------------------------------

def _handle_sigint(sig, frame):
    """Handle Ctrl+C gracefully without tracebacks."""
    print(f"\n\n  Interrupted. Progress has been saved — run ac-phase again to resume.")
    sys.exit(0)

signal.signal(signal.SIGINT, _handle_sigint)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTO_CLAUDE_ROOT = Path(__file__).resolve().parent.parent
RUN_PY = AUTO_CLAUDE_ROOT / "apps" / "backend" / "run.py"
SPEC_RUNNER_PY = AUTO_CLAUDE_ROOT / "apps" / "backend" / "runners" / "spec_runner.py"
VENV_PYTHON = AUTO_CLAUDE_ROOT / "apps" / "backend" / ".venv" / "bin" / "python"

# Category → recommended execution order (lower = earlier)
CATEGORY_PRIORITY = {
    "sec": 1,       # Security first
    "cq": 2,        # Code quality / refactors
    "ci": 3,        # Code improvements / utilities
    "perf": 4,      # Performance
    "uiux": 5,      # UI/UX features
    "doc": 6,       # Documentation last
}

# Phase display names
CATEGORY_NAMES = {
    "sec": "Security Hardening",
    "cq": "Code Quality",
    "ci": "Code Improvements",
    "perf": "Performance",
    "uiux": "UI/UX Improvements",
    "doc": "Documentation",
}

# Status markers (what files indicate spec state)
STATUS_FILES = [
    ("qa_report.md", "qa_passed"),
    ("build_log.md", "built"),
    ("spec.md", "spec_ready"),
    ("implementation_plan.json", "planned"),
    ("requirements.json", "pending"),
]

# Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"

STATUS_ICONS = {
    "qa_passed": f"{C_GREEN}✅{C_RESET}",
    "built": f"{C_BLUE}⚙️{C_RESET}",
    "spec_ready": f"{C_CYAN}📋{C_RESET}",
    "planned": f"{C_YELLOW}📐{C_RESET}",
    "pending": f"{C_YELLOW}⏳{C_RESET}",
    "failed": f"{C_RED}❌{C_RESET}",
    "running": f"{C_MAGENTA}▶{C_RESET}",
}

PHASE_STATUS_ICONS = {
    "complete": f"{C_GREEN}✅{C_RESET}",
    "in_progress": f"{C_MAGENTA}▶{C_RESET}",
    "pending": f"{C_DIM}○{C_RESET}",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_project_dir():
    """Walk up from cwd to find a directory with .auto-claude/specs/."""
    d = Path.cwd()
    while d != d.parent:
        if (d / ".auto-claude" / "specs").is_dir():
            return d
        d = d.parent
    return None


def get_specs_dir(project_dir):
    return project_dir / ".auto-claude" / "specs"


def get_phases_file(project_dir):
    return project_dir / ".auto-claude" / "phases.json"


def get_phase_state_file(project_dir):
    return project_dir / ".auto-claude" / "phase_state.json"


def parse_spec_id(spec_name):
    """Extract numeric ID from spec directory name like '016-[sec-001]-fix-...'."""
    match = re.match(r"^(\d+)", spec_name)
    return match.group(1) if match else None


def parse_category(spec_name):
    """Extract category prefix from spec name like '016-[sec-001]-...' → 'sec'."""
    match = re.search(r"\[(\w+)-\d+\]", spec_name)
    return match.group(1) if match else "other"


def get_spec_status(spec_dir):
    """Determine current status of a spec based on marker files."""
    for filename, status in STATUS_FILES:
        if (spec_dir / filename).exists():
            return status
    return "pending"


def get_spec_title(spec_dir):
    """Get human-readable title from requirements.json."""
    req_file = spec_dir / "requirements.json"
    if req_file.exists():
        try:
            with open(req_file) as f:
                data = json.load(f)
                desc = data.get("task_description", "")
                # Truncate to first sentence or 80 chars
                if "\n" in desc:
                    desc = desc.split("\n")[0]
                return desc[:100]
        except (json.JSONDecodeError, KeyError):
            pass
    # Fallback: clean up directory name
    name = spec_dir.name
    name = re.sub(r"^\d+-", "", name)
    name = re.sub(r"\[[\w-]+\]-?", "", name)
    return name.replace("-", " ").strip().title()


def load_all_specs(project_dir):
    """Load all specs with metadata."""
    specs_dir = get_specs_dir(project_dir)
    specs = []
    for d in sorted(specs_dir.iterdir()):
        if not d.is_dir():
            continue
        spec_id = parse_spec_id(d.name)
        if not spec_id:
            continue
        specs.append({
            "id": spec_id,
            "name": d.name,
            "category": parse_category(d.name),
            "status": get_spec_status(d),
            "title": get_spec_title(d),
            "dir": d,
        })
    return specs


def load_phases(project_dir):
    """Load phases.json or return None if not found."""
    pf = get_phases_file(project_dir)
    if not pf.exists():
        return None
    with open(pf) as f:
        return json.load(f)


def save_phases(project_dir, phases_data):
    """Save phases.json."""
    pf = get_phases_file(project_dir)
    with open(pf, "w") as f:
        json.dump(phases_data, f, indent=2)
    print(f"  {C_GREEN}✓{C_RESET} Saved {pf}")


def load_phase_state(project_dir):
    """Load phase execution state (which phases completed, failures, etc.)."""
    sf = get_phase_state_file(project_dir)
    if sf.exists():
        with open(sf) as f:
            return json.load(f)
    return {"completed_phases": [], "failed_specs": [], "current_phase": None}


def save_phase_state(project_dir, state):
    sf = get_phase_state_file(project_dir)
    with open(sf, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Phase generation
# ---------------------------------------------------------------------------

def auto_generate_phases(project_dir, specs):
    """Auto-generate phases.json by grouping specs by category."""
    groups = defaultdict(list)
    for s in specs:
        groups[s["category"]].append(s["id"])

    # Sort categories by recommended priority
    sorted_cats = sorted(
        groups.keys(),
        key=lambda c: CATEGORY_PRIORITY.get(c, 99)
    )

    phases = []
    for idx, cat in enumerate(sorted_cats, 1):
        spec_ids = sorted(groups[cat])
        name = CATEGORY_NAMES.get(cat, cat.upper())
        phases.append({
            "phase": idx,
            "name": name,
            "category": cat,
            "specs": spec_ids,
            "parallel": False,
        })

    phases_data = {
        "version": 1,
        "pause_between_phases": True,
        "auto_qa": True,
        "phases": phases,
    }

    save_phases(project_dir, phases_data)
    return phases_data


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_header(text):
    width = 64
    print()
    print(f"  {C_BOLD}{'═' * width}{C_RESET}")
    print(f"  {C_BOLD}  {text}{C_RESET}")
    print(f"  {C_BOLD}{'═' * width}{C_RESET}")
    print()


def print_phase_status(project_dir, phases_data, specs):
    """Display full status of all phases and their specs."""
    spec_map = {s["id"]: s for s in specs}
    state = load_phase_state(project_dir)
    completed_phases = state.get("completed_phases", [])

    total_specs = sum(len(p["specs"]) for p in phases_data["phases"])
    done_specs = sum(1 for s in specs if s["status"] in ("qa_passed", "built"))
    pct = int(done_specs / total_specs * 100) if total_specs > 0 else 0

    # Progress bar
    bar_width = 40
    filled = int(bar_width * pct / 100)
    bar = f"{'█' * filled}{'░' * (bar_width - filled)}"
    print(f"  Progress: [{bar}] {pct}% ({done_specs}/{total_specs} specs)")
    print()

    for phase in phases_data["phases"]:
        phase_num = phase["phase"]
        phase_name = phase["name"]
        phase_specs = phase["specs"]

        # Determine phase status
        spec_statuses = [spec_map.get(sid, {}).get("status", "pending") for sid in phase_specs]
        all_done = all(s in ("qa_passed", "built") for s in spec_statuses)
        any_started = any(s != "pending" for s in spec_statuses)

        if all_done or phase_num in completed_phases:
            phase_icon = PHASE_STATUS_ICONS["complete"]
            phase_color = C_GREEN
        elif any_started:
            phase_icon = PHASE_STATUS_ICONS["in_progress"]
            phase_color = C_MAGENTA
        else:
            phase_icon = PHASE_STATUS_ICONS["pending"]
            phase_color = C_DIM

        done_in_phase = sum(1 for s in spec_statuses if s in ("qa_passed", "built"))
        print(f"  {phase_icon} {phase_color}Phase {phase_num}: {phase_name}{C_RESET} ({done_in_phase}/{len(phase_specs)})")

        for sid in phase_specs:
            s = spec_map.get(sid)
            if not s:
                print(f"      {C_RED}?{C_RESET} {sid} — spec not found")
                continue
            icon = STATUS_ICONS.get(s["status"], "?")
            title = s["title"][:70]
            print(f"      {icon} {C_DIM}{sid}{C_RESET} {title}")

        print()


def print_menu(phases_data, project_dir, specs):
    """Print interactive menu options."""
    state = load_phase_state(project_dir)
    completed = state.get("completed_phases", [])

    # Find next phase
    next_phase = None
    for p in phases_data["phases"]:
        if p["phase"] not in completed:
            next_phase = p
            break

    print(f"  {C_BOLD}What would you like to do?{C_RESET}")
    print()
    if next_phase:
        print(f"    {C_CYAN}1){C_RESET} Run next phase → {C_BOLD}Phase {next_phase['phase']}: {next_phase['name']}{C_RESET}")
    else:
        print(f"    {C_GREEN}1) All phases complete!{C_RESET}")
    print(f"    {C_CYAN}2){C_RESET} Run a specific phase")
    print(f"    {C_CYAN}3){C_RESET} Run all remaining phases")
    print(f"    {C_CYAN}4){C_RESET} View detailed status")
    print(f"    {C_CYAN}5){C_RESET} Regenerate phases (re-read specs)")
    print(f"    {C_CYAN}6){C_RESET} Reset phase progress")
    print(f"    {C_CYAN}q){C_RESET} Quit")
    print()

    return next_phase


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def find_spec_dir_name(project_dir, spec_id):
    """Find the full directory name for a spec ID (e.g. '016' → '016-[sec-001]-fix-...')."""
    specs_dir = get_specs_dir(project_dir)
    for d in specs_dir.iterdir():
        if d.is_dir() and d.name.startswith(spec_id + "-"):
            return d.name
    return None


def spec_needs_generation(project_dir, spec_id):
    """Check if a spec still needs spec.md generated (only has requirements.json)."""
    specs_dir = get_specs_dir(project_dir)
    for d in specs_dir.iterdir():
        if d.is_dir() and d.name.startswith(spec_id + "-"):
            return not (d / "spec.md").exists()
    return False


def run_spec(project_dir, spec_id, auto_qa=True):
    """Run a single spec through Auto-Claude (generate spec → build → optional QA)."""
    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"
    run_py = str(RUN_PY)
    spec_runner_py = str(SPEC_RUNNER_PY)

    spec_dir_name = find_spec_dir_name(project_dir, spec_id)
    if not spec_dir_name:
        print(f"  {C_RED}✗ Spec {spec_id} directory not found{C_RESET}")
        return False

    # Step 1: Generate spec.md if it doesn't exist yet
    if spec_needs_generation(project_dir, spec_id):
        print(f"\n  {C_CYAN}▸ Generating spec for {spec_id}...{C_RESET}")
        gen_cmd = [
            python, spec_runner_py,
            "--project-dir", str(project_dir),
            "--continue", spec_dir_name,
            "--auto-approve",
        ]
        print(f"    {C_DIM}$ {' '.join(gen_cmd)}{C_RESET}")

        try:
            result = subprocess.run(gen_cmd, cwd=str(project_dir))
        except KeyboardInterrupt:
            print(f"\n  {C_YELLOW}⚠ Spec generation for {spec_id} interrupted{C_RESET}")
            return False
        if result.returncode != 0:
            print(f"  {C_RED}✗ Spec generation for {spec_id} failed (exit {result.returncode}){C_RESET}")
            return False

        # Verify spec.md was created
        if spec_needs_generation(project_dir, spec_id):
            print(f"  {C_RED}✗ spec.md was not created for {spec_id}{C_RESET}")
            return False

        print(f"  {C_GREEN}✓ Spec {spec_id} generated{C_RESET}")

    # Step 2: Build
    print(f"\n  {C_CYAN}▸ Building spec {spec_id}...{C_RESET}")
    build_cmd = [python, run_py, "--project-dir", str(project_dir), "--spec", spec_id]
    print(f"    {C_DIM}$ {' '.join(build_cmd)}{C_RESET}")

    try:
        result = subprocess.run(build_cmd, cwd=str(project_dir))
    except KeyboardInterrupt:
        print(f"\n  {C_YELLOW}⚠ Build for spec {spec_id} interrupted{C_RESET}")
        return False

    if result.returncode != 0:
        print(f"  {C_RED}✗ Build for spec {spec_id} failed (exit {result.returncode}){C_RESET}")
        return False

    # Step 3: QA (optional)
    if auto_qa:
        print(f"\n  {C_CYAN}▸ QA validating spec {spec_id}...{C_RESET}")
        qa_cmd = [python, run_py, "--project-dir", str(project_dir), "--spec", spec_id, "--qa"]
        print(f"    {C_DIM}$ {' '.join(qa_cmd)}{C_RESET}")
        try:
            qa_result = subprocess.run(qa_cmd, cwd=str(project_dir))
        except KeyboardInterrupt:
            print(f"\n  {C_YELLOW}⚠ QA for spec {spec_id} interrupted{C_RESET}")
            return False
        if qa_result.returncode != 0:
            print(f"  {C_YELLOW}⚠ QA for spec {spec_id} returned warnings{C_RESET}")

    print(f"  {C_GREEN}✓ Spec {spec_id} complete{C_RESET}")
    return True


def run_phase(project_dir, phase, phases_data, specs):
    """Execute all specs in a phase."""
    state = load_phase_state(project_dir)
    auto_qa = phases_data.get("auto_qa", True)
    spec_map = {s["id"]: s for s in specs}

    phase_num = phase["phase"]
    phase_name = phase["name"]
    phase_specs = phase["specs"]

    # Filter to only pending/unbuilt specs
    pending = [
        sid for sid in phase_specs
        if spec_map.get(sid, {}).get("status", "pending") not in ("qa_passed", "built")
    ]

    if not pending:
        print(f"\n  {C_GREEN}✓ Phase {phase_num}: {phase_name} — all specs already complete{C_RESET}")
        if phase_num not in state["completed_phases"]:
            state["completed_phases"].append(phase_num)
            save_phase_state(project_dir, state)
        return True

    print_header(f"Phase {phase_num}: {phase_name}")
    print(f"  Running {len(pending)} spec(s): {', '.join(pending)}")
    print()

    state["current_phase"] = phase_num
    save_phase_state(project_dir, state)

    failed = []
    succeeded = []

    for sid in pending:
        success = run_spec(project_dir, sid, auto_qa=auto_qa)
        if success:
            succeeded.append(sid)
        else:
            failed.append(sid)
            if sid not in state["failed_specs"]:
                state["failed_specs"].append(sid)
            save_phase_state(project_dir, state)

    # Phase summary
    print()
    print(f"  {'─' * 50}")
    print(f"  Phase {phase_num} summary: {C_GREEN}{len(succeeded)} passed{C_RESET}", end="")
    if failed:
        print(f", {C_RED}{len(failed)} failed ({', '.join(failed)}){C_RESET}")
    else:
        print()

    if not failed:
        state["completed_phases"].append(phase_num)
    state["current_phase"] = None
    save_phase_state(project_dir, state)

    return len(failed) == 0


def run_all_phases(project_dir, phases_data, specs, pause=True):
    """Run all remaining phases in order."""
    state = load_phase_state(project_dir)
    completed = state.get("completed_phases", [])

    remaining = [p for p in phases_data["phases"] if p["phase"] not in completed]

    if not remaining:
        print(f"\n  {C_GREEN}✓ All phases already complete!{C_RESET}")
        return

    for i, phase in enumerate(remaining):
        success = run_phase(project_dir, phase, phases_data, specs)

        # Refresh specs after each phase (statuses may have changed)
        specs = load_all_specs(project_dir)

        if not success:
            print(f"\n  {C_YELLOW}⚠ Phase {phase['phase']} had failures. Continue? [y/N]{C_RESET} ", end="")
            ans = input().strip().lower()
            if ans != "y":
                print("  Stopping. Fix failures and re-run.")
                return

        # Pause between phases for review
        if pause and i < len(remaining) - 1:
            next_p = remaining[i + 1]
            print(f"\n  {C_CYAN}▸ Next up: Phase {next_p['phase']}: {next_p['name']}{C_RESET}")
            print(f"  {C_BOLD}Continue to next phase? [Y/n]{C_RESET} ", end="")
            ans = input().strip().lower()
            if ans == "n":
                print("  Paused. Run ac-phase again to continue.")
                return

    print(f"\n  {C_GREEN}{'═' * 50}{C_RESET}")
    print(f"  {C_GREEN}  All phases complete!{C_RESET}")
    print(f"  {C_GREEN}{'═' * 50}{C_RESET}")


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive(project_dir):
    """Main interactive loop."""
    specs = load_all_specs(project_dir)

    if not specs:
        print(f"  {C_RED}No specs found in {get_specs_dir(project_dir)}{C_RESET}")
        print("  Run ac-batch first to create specs from ideation.")
        return

    # Load or generate phases
    phases_data = load_phases(project_dir)
    if not phases_data:
        print(f"  {C_YELLOW}No phases.json found. Generating from spec categories...{C_RESET}")
        phases_data = auto_generate_phases(project_dir, specs)
        print()

    project_name = project_dir.name
    print_header(f"ac-phase — {project_name}")
    print_phase_status(project_dir, phases_data, specs)

    while True:
        next_phase = print_menu(phases_data, project_dir, specs)

        try:
            choice = input(f"  {C_BOLD}>{C_RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  Progress saved. Run ac-phase again to resume.")
            break

        if choice == "q":
            print("  Bye!")
            break

        elif choice == "1":
            if next_phase:
                run_phase(project_dir, next_phase, phases_data, specs)
                specs = load_all_specs(project_dir)  # Refresh
                print()
                print_phase_status(project_dir, phases_data, specs)
            else:
                print(f"  {C_GREEN}All phases are complete!{C_RESET}")

        elif choice == "2":
            print(f"\n  Which phase? (1-{len(phases_data['phases'])}): ", end="")
            try:
                pnum = int(input().strip())
                phase = next((p for p in phases_data["phases"] if p["phase"] == pnum), None)
                if phase:
                    run_phase(project_dir, phase, phases_data, specs)
                    specs = load_all_specs(project_dir)
                    print()
                    print_phase_status(project_dir, phases_data, specs)
                else:
                    print(f"  {C_RED}Phase {pnum} not found{C_RESET}")
            except ValueError:
                print(f"  {C_RED}Invalid input{C_RESET}")

        elif choice == "3":
            pause = phases_data.get("pause_between_phases", True)
            run_all_phases(project_dir, phases_data, specs, pause=pause)
            specs = load_all_specs(project_dir)
            print()
            print_phase_status(project_dir, phases_data, specs)

        elif choice == "4":
            print()
            print_phase_status(project_dir, phases_data, specs)

        elif choice == "5":
            phases_data = auto_generate_phases(project_dir, specs)
            print()
            print_phase_status(project_dir, phases_data, specs)

        elif choice == "6":
            save_phase_state(project_dir, {
                "completed_phases": [],
                "failed_specs": [],
                "current_phase": None,
            })
            print(f"  {C_GREEN}✓ Phase progress reset{C_RESET}")
            print()
            specs = load_all_specs(project_dir)
            print_phase_status(project_dir, phases_data, specs)

        else:
            print(f"  {C_DIM}Unknown option. Try 1-6 or q.{C_RESET}")

        print()


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive phased spec executor for Auto-Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ac-phase                     Interactive menu
  ac-phase --status            Show phase status
  ac-phase --run               Run next pending phase
  ac-phase --run --phase 2     Run phase 2
  ac-phase --run --all         Run all remaining phases
  ac-phase --init              Generate phases.json from specs
        """,
    )
    parser.add_argument("--project-dir", type=Path, default=None,
                        help="Project directory (default: auto-detect from cwd)")
    parser.add_argument("--status", action="store_true",
                        help="Show phase and spec status")
    parser.add_argument("--run", action="store_true",
                        help="Run phases (next by default)")
    parser.add_argument("--phase", type=int, default=None,
                        help="Specific phase number to run (with --run)")
    parser.add_argument("--all", action="store_true",
                        help="Run all remaining phases (with --run)")
    parser.add_argument("--no-pause", action="store_true",
                        help="Don't pause between phases (with --run --all)")
    parser.add_argument("--init", action="store_true",
                        help="Generate/regenerate phases.json from specs")
    parser.add_argument("--edit", action="store_true",
                        help="Open phases.json in $EDITOR")

    args = parser.parse_args()

    # Find project
    if args.project_dir:
        project_dir = args.project_dir.resolve()
    else:
        project_dir = find_project_dir()

    if not project_dir:
        print(f"  {C_RED}Error: No .auto-claude/specs/ found.{C_RESET}")
        print("  Run this from inside a project with Auto-Claude specs,")
        print("  or pass --project-dir /path/to/project")
        sys.exit(1)

    specs = load_all_specs(project_dir)

    # --init: generate phases
    if args.init:
        auto_generate_phases(project_dir, specs)
        return

    # --edit: open in editor
    if args.edit:
        pf = get_phases_file(project_dir)
        if not pf.exists():
            auto_generate_phases(project_dir, specs)
        editor = os.environ.get("EDITOR", "nano")
        os.execvp(editor, [editor, str(pf)])
        return

    # Ensure phases exist
    phases_data = load_phases(project_dir)
    if not phases_data:
        if args.status or args.run:
            print(f"  {C_YELLOW}No phases.json found. Generating...{C_RESET}")
            phases_data = auto_generate_phases(project_dir, specs)
        else:
            # Interactive mode will handle it
            interactive(project_dir)
            return

    # --status: just display
    if args.status:
        print_header(f"ac-phase — {project_dir.name}")
        print_phase_status(project_dir, phases_data, specs)
        return

    # --run: execute phases
    if args.run:
        if args.all:
            run_all_phases(project_dir, phases_data, specs, pause=not args.no_pause)
        elif args.phase:
            phase = next((p for p in phases_data["phases"] if p["phase"] == args.phase), None)
            if not phase:
                print(f"  {C_RED}Phase {args.phase} not found{C_RESET}")
                sys.exit(1)
            run_phase(project_dir, phase, phases_data, specs)
        else:
            # Run next pending phase
            state = load_phase_state(project_dir)
            completed = state.get("completed_phases", [])
            next_phase = next(
                (p for p in phases_data["phases"] if p["phase"] not in completed),
                None
            )
            if next_phase:
                run_phase(project_dir, next_phase, phases_data, specs)
            else:
                print(f"  {C_GREEN}✓ All phases complete!{C_RESET}")
        return

    # Default: interactive mode
    interactive(project_dir)


if __name__ == "__main__":
    main()
