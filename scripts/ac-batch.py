#!/usr/bin/env python3
"""
ac-batch — Interactive batch task manager for Auto-Claude
==========================================================

Create, manage, build, and track batches of specs from discovery
outputs (ideation, roadmap, insights) or manual batch JSON files.

Usage:
    ac-batch                          # Interactive menu (auto-detects project)
    ac-batch --insights               # Interactive codebase Q&A chat
    ac-batch --insights "question"    # One-shot codebase question
    ac-batch --status                 # Show all spec statuses
    ac-batch --create tasks.json      # Create specs from batch JSON file
    ac-batch --discover               # Create batch from discovery outputs
    ac-batch --build                  # Build all pending specs sequentially
    ac-batch --build --spec 016       # Build a specific spec
    ac-batch --qa                     # QA all built specs
    ac-batch --cleanup                # Show what would be cleaned up
    ac-batch --cleanup --confirm      # Actually delete completed specs
"""

import argparse
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
    print(f"\n\n  Interrupted. Progress saved — run ac-batch again to resume.")
    sys.exit(0)

signal.signal(signal.SIGINT, _handle_sigint)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTO_CLAUDE_ROOT = Path(__file__).resolve().parent.parent
RUN_PY = AUTO_CLAUDE_ROOT / "apps" / "backend" / "run.py"
SPEC_RUNNER_PY = AUTO_CLAUDE_ROOT / "apps" / "backend" / "runners" / "spec_runner.py"
INSIGHTS_RUNNER_PY = AUTO_CLAUDE_ROOT / "apps" / "backend" / "runners" / "insights_runner.py"
VENV_PYTHON = AUTO_CLAUDE_ROOT / "apps" / "backend" / ".venv" / "bin" / "python"
BATCH_FROM_DISCOVERY = Path(__file__).resolve().parent / "batch-from-discovery.py"

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
}

STATUS_LABELS = {
    "qa_passed": "QA Passed",
    "built": "Built",
    "spec_ready": "Spec Ready",
    "planned": "Planned",
    "pending": "Pending",
    "failed": "Failed",
}

# Status marker files (checked in order — first match wins)
STATUS_FILES = [
    ("qa_report.md", "qa_passed"),
    ("build_log.md", "built"),
    ("spec.md", "spec_ready"),
    ("implementation_plan.json", "planned"),
    ("requirements.json", "pending"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_python():
    return str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"


def find_project_dir():
    """Walk up from cwd to find a directory with .auto-claude/."""
    d = Path.cwd()
    while d != d.parent:
        if (d / ".auto-claude").is_dir():
            return d
        d = d.parent
    return None


def get_specs_dir(project_dir):
    return project_dir / ".auto-claude" / "specs"


def parse_spec_id(spec_name):
    match = re.match(r"^(\d+)", spec_name)
    return match.group(1) if match else None


def parse_category(spec_name):
    match = re.search(r"\[(\w+)-\d+\]", spec_name)
    return match.group(1) if match else "other"


def get_spec_status(spec_dir):
    for filename, status in STATUS_FILES:
        if (spec_dir / filename).exists():
            return status
    return "pending"


def get_spec_title(spec_dir):
    req_file = spec_dir / "requirements.json"
    if req_file.exists():
        try:
            with open(req_file) as f:
                data = json.load(f)
                desc = data.get("task_description", "")
                if "\n" in desc:
                    desc = desc.split("\n")[0]
                return desc[:100]
        except (json.JSONDecodeError, KeyError):
            pass
    name = spec_dir.name
    name = re.sub(r"^\d+-", "", name)
    name = re.sub(r"\[[\w-]+\]-?", "", name)
    return name.replace("-", " ").strip().title()


def load_all_specs(project_dir):
    specs_dir = get_specs_dir(project_dir)
    if not specs_dir.exists():
        return []
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


def prompt_yn(question, default=True):
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {C_BOLD}{question}{C_RESET} [{hint}] ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def prompt_choice(question, options, allow_multi=False):
    """Numbered menu. Returns list of selected indices."""
    print(f"  {C_BOLD}{question}{C_RESET}")
    print()
    for i, (label, detail) in enumerate(options, 1):
        detail_str = f" {C_DIM}— {detail}{C_RESET}" if detail else ""
        print(f"    {C_CYAN}{i:>3}{C_RESET}) {label}{detail_str}")
    print(f"    {C_CYAN}  q{C_RESET}) Cancel")
    print()

    while True:
        raw = input(f"  {C_BOLD}>{C_RESET} ").strip().lower()
        if raw == "q":
            return []
        try:
            if allow_multi and ("," in raw or " " in raw):
                parts = raw.replace(",", " ").split()
                indices = [int(p) - 1 for p in parts]
                if all(0 <= i < len(options) for i in indices):
                    return indices
            else:
                idx = int(raw) - 1
                if 0 <= idx < len(options):
                    return [idx]
        except ValueError:
            pass
        print(f"  {C_YELLOW}Invalid choice.{C_RESET}")


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


def print_status_table(specs):
    """Display spec status table with summary."""
    if not specs:
        print(f"  {C_DIM}No specs found.{C_RESET}")
        return

    # Group by status for summary
    by_status = defaultdict(list)
    for s in specs:
        by_status[s["status"]].append(s)

    # Summary bar
    total = len(specs)
    parts = []
    for status in ["qa_passed", "built", "spec_ready", "planned", "pending"]:
        count = len(by_status.get(status, []))
        if count > 0:
            label = STATUS_LABELS.get(status, status)
            parts.append(f"{label}: {count}")
    print(f"  {C_BOLD}{total} specs{C_RESET} — {', '.join(parts)}")
    print()

    # Progress bar
    done = len(by_status.get("qa_passed", [])) + len(by_status.get("built", []))
    pct = int(done / total * 100) if total > 0 else 0
    bar_width = 40
    filled = int(bar_width * pct / 100)
    bar = f"{'█' * filled}{'░' * (bar_width - filled)}"
    print(f"  Progress: [{bar}] {pct}% ({done}/{total} complete)")
    print()

    # Group by category
    by_category = defaultdict(list)
    for s in specs:
        by_category[s["category"]].append(s)

    for cat in sorted(by_category.keys()):
        cat_specs = by_category[cat]
        print(f"  {C_CYAN}{C_BOLD}{cat.upper()}{C_RESET} ({len(cat_specs)} specs)")
        for s in cat_specs:
            icon = STATUS_ICONS.get(s["status"], "?")
            title = s["title"][:65]
            print(f"    {icon} {C_DIM}{s['id']}{C_RESET} {title}")
        print()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_create_from_file(project_dir, batch_file):
    """Create specs from a batch JSON file using run.py --batch-create."""
    batch_path = Path(batch_file)
    if not batch_path.exists():
        print(f"  {C_RED}Batch file not found: {batch_file}{C_RESET}")
        return False

    try:
        with open(batch_path) as f:
            data = json.load(f)
        task_count = len(data.get("tasks", []))
    except (json.JSONDecodeError, KeyError):
        print(f"  {C_RED}Invalid batch JSON file{C_RESET}")
        return False

    print(f"  {C_CYAN}Creating {task_count} specs from {batch_path.name}...{C_RESET}")
    print()

    python = get_python()
    cmd = [python, str(RUN_PY), "--project-dir", str(project_dir),
           "--batch-create", str(batch_path)]
    print(f"  {C_DIM}$ {' '.join(cmd)}{C_RESET}")
    print()

    result = subprocess.run(cmd, cwd=str(project_dir))
    return result.returncode == 0


def action_discover(project_dir):
    """Launch the interactive discovery-to-batch workflow."""
    if not BATCH_FROM_DISCOVERY.exists():
        print(f"  {C_RED}batch-from-discovery.py not found at:{C_RESET}")
        print(f"  {BATCH_FROM_DISCOVERY}")
        return False

    python = get_python()
    cmd = [python, str(BATCH_FROM_DISCOVERY), str(project_dir),
           "--auto-claude-dir", str(AUTO_CLAUDE_ROOT)]
    result = subprocess.run(cmd, cwd=str(project_dir))
    return result.returncode == 0


def action_build_spec(project_dir, spec_id, generate_spec=True, run_qa=False):
    """Build a single spec (optionally generate spec.md first, optionally QA)."""
    python = get_python()

    # Step 1: Generate spec.md if needed
    if generate_spec:
        specs_dir = get_specs_dir(project_dir)
        spec_dir = None
        for d in specs_dir.iterdir():
            if d.is_dir() and d.name.startswith(spec_id + "-"):
                spec_dir = d
                break

        if spec_dir and not (spec_dir / "spec.md").exists():
            print(f"  {C_CYAN}Generating spec for {spec_id}...{C_RESET}")
            gen_cmd = [python, str(SPEC_RUNNER_PY),
                       "--project-dir", str(project_dir),
                       "--continue", spec_dir.name,
                       "--auto-approve"]
            print(f"  {C_DIM}$ {' '.join(gen_cmd)}{C_RESET}")
            try:
                result = subprocess.run(gen_cmd, cwd=str(project_dir))
            except KeyboardInterrupt:
                print(f"\n  {C_YELLOW}Spec generation interrupted{C_RESET}")
                return False
            if result.returncode != 0:
                print(f"  {C_RED}Spec generation failed for {spec_id}{C_RESET}")
                return False

    # Step 2: Build
    print(f"  {C_CYAN}Building spec {spec_id}...{C_RESET}")
    build_cmd = [python, str(RUN_PY), "--project-dir", str(project_dir),
                 "--spec", spec_id]
    print(f"  {C_DIM}$ {' '.join(build_cmd)}{C_RESET}")

    try:
        result = subprocess.run(build_cmd, cwd=str(project_dir))
    except KeyboardInterrupt:
        print(f"\n  {C_YELLOW}Build interrupted for {spec_id}{C_RESET}")
        return False

    if result.returncode != 0:
        print(f"  {C_RED}Build failed for {spec_id}{C_RESET}")
        return False

    # Step 3: QA (optional)
    if run_qa:
        print(f"  {C_CYAN}Running QA for {spec_id}...{C_RESET}")
        qa_cmd = [python, str(RUN_PY), "--project-dir", str(project_dir),
                  "--spec", spec_id, "--qa"]
        print(f"  {C_DIM}$ {' '.join(qa_cmd)}{C_RESET}")
        try:
            subprocess.run(qa_cmd, cwd=str(project_dir))
        except KeyboardInterrupt:
            print(f"\n  {C_YELLOW}QA interrupted for {spec_id}{C_RESET}")
            return False

    print(f"  {C_GREEN}✓ Spec {spec_id} done{C_RESET}")
    return True


def action_build_all(project_dir, run_qa=False, statuses=("pending", "spec_ready")):
    """Build all specs that match the given statuses."""
    specs = load_all_specs(project_dir)
    targets = [s for s in specs if s["status"] in statuses]

    if not targets:
        print(f"  {C_GREEN}No specs need building.{C_RESET}")
        return True

    print(f"  {C_BOLD}Building {len(targets)} spec(s):{C_RESET}")
    for s in targets:
        print(f"    {s['id']} — {s['title'][:60]}")
    print()

    if not prompt_yn(f"Proceed with building {len(targets)} specs?"):
        print("  Cancelled.")
        return False

    succeeded = []
    failed = []

    for i, s in enumerate(targets, 1):
        print()
        print(f"  {C_BOLD}[{i}/{len(targets)}]{C_RESET} {s['id']} — {s['title'][:50]}")
        print(f"  {'─' * 50}")

        ok = action_build_spec(project_dir, s["id"], generate_spec=True, run_qa=run_qa)
        if ok:
            succeeded.append(s["id"])
        else:
            failed.append(s["id"])
            if not prompt_yn("Continue with remaining specs?"):
                break

    # Summary
    print()
    print(f"  {'═' * 50}")
    print(f"  {C_GREEN}Succeeded: {len(succeeded)}{C_RESET}", end="")
    if failed:
        print(f"  {C_RED}Failed: {len(failed)} ({', '.join(failed)}){C_RESET}")
    else:
        print()

    return len(failed) == 0


def action_qa_all(project_dir):
    """Run QA on all built (but not QA'd) specs."""
    specs = load_all_specs(project_dir)
    targets = [s for s in specs if s["status"] == "built"]

    if not targets:
        print(f"  {C_GREEN}No specs awaiting QA.{C_RESET}")
        return True

    python = get_python()
    print(f"  {C_BOLD}Running QA on {len(targets)} spec(s):{C_RESET}")
    for s in targets:
        print(f"    {s['id']} — {s['title'][:60]}")
    print()

    for i, s in enumerate(targets, 1):
        print(f"  {C_CYAN}[{i}/{len(targets)}] QA for {s['id']}...{C_RESET}")
        qa_cmd = [python, str(RUN_PY), "--project-dir", str(project_dir),
                  "--spec", s["id"], "--qa"]
        print(f"  {C_DIM}$ {' '.join(qa_cmd)}{C_RESET}")
        try:
            subprocess.run(qa_cmd, cwd=str(project_dir))
        except KeyboardInterrupt:
            print(f"\n  {C_YELLOW}QA interrupted{C_RESET}")
            return False

    return True


def action_insights(project_dir, message=None):
    """Run an insights query against the project codebase."""
    python = get_python()
    backend_dir = AUTO_CLAUDE_ROOT / "apps" / "backend"

    if message:
        # One-shot mode
        print(f"  {C_CYAN}Asking about {project_dir.name}...{C_RESET}")
        print(f"  {C_DIM}Q: {message}{C_RESET}")
        print()
        cmd = [python, "-m", "runners.insights_runner",
               "--project-dir", str(project_dir),
               "--message", message]
        try:
            result = subprocess.run(cmd, cwd=str(backend_dir))
        except KeyboardInterrupt:
            print(f"\n  {C_YELLOW}Interrupted{C_RESET}")
            return False
        return result.returncode == 0

    # Interactive chat mode
    print_header(f"Insights — {project_dir.name}")
    print(f"  {C_BOLD}Ask questions about your codebase.{C_RESET}")
    print(f"  {C_DIM}Type your question and press Enter. Type 'q' to go back.{C_RESET}")
    print()

    # Suggested questions
    print(f"  {C_BOLD}Suggested questions:{C_RESET}")
    suggestions = [
        "What is the overall architecture?",
        "What are the main API endpoints?",
        "Are there any security concerns?",
        "What features are missing for production readiness?",
        "What are the biggest technical debt items?",
        "How does authentication work?",
        "What error handling patterns are used?",
        "What would need to change to add a new feature?",
    ]
    for i, q in enumerate(suggestions, 1):
        print(f"    {C_CYAN}{i}){C_RESET} {q}")
    print()

    history_file = project_dir / ".auto-claude" / "insights" / "ac-batch-history.json"
    history = []

    while True:
        try:
            raw = input(f"  {C_BOLD}?{C_RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not raw or raw.lower() == "q":
            break

        # Allow selecting a suggested question by number
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(suggestions):
                raw = suggestions[idx]
                print(f"  {C_DIM}Q: {raw}{C_RESET}")
        except ValueError:
            pass

        # Build command
        cmd = [python, "-m", "runners.insights_runner",
               "--project-dir", str(project_dir),
               "--message", raw]

        # Pass conversation history if we have prior messages
        if history:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            history_file.write_text(json.dumps(history))
            cmd.extend(["--history-file", str(history_file)])

        print()
        try:
            result = subprocess.run(cmd, cwd=str(backend_dir),
                                    capture_output=False)
        except KeyboardInterrupt:
            print(f"\n  {C_YELLOW}Interrupted{C_RESET}")
            continue

        # Track conversation for context
        history.append({"role": "user", "content": raw})
        history.append({"role": "assistant", "content": "(see above)"})

        print()

    # Clean up temp history file
    if history_file.exists():
        history_file.unlink()

    return True


def action_cleanup(project_dir, confirm=False):
    """Clean up completed specs."""
    python = get_python()
    cmd = [python, str(RUN_PY), "--project-dir", str(project_dir), "--batch-cleanup"]
    if confirm:
        cmd.append("--no-dry-run")

    result = subprocess.run(cmd, cwd=str(project_dir))
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive(project_dir):
    """Main interactive loop."""
    project_name = project_dir.name

    while True:
        specs = load_all_specs(project_dir)
        print_header(f"ac-batch — {project_name}")
        print_status_table(specs)

        # Menu
        print(f"  {C_BOLD}What would you like to do?{C_RESET}")
        print()
        print(f"    {C_CYAN}1){C_RESET} Ask about the codebase (insights)")
        print(f"    {C_CYAN}2){C_RESET} Create batch from discovery outputs (ideation/roadmap/insights)")
        print(f"    {C_CYAN}3){C_RESET} Create batch from JSON file")
        print(f"    {C_CYAN}4){C_RESET} Build all pending specs")
        print(f"    {C_CYAN}5){C_RESET} Build a specific spec")
        print(f"    {C_CYAN}6){C_RESET} QA all built specs")
        print(f"    {C_CYAN}7){C_RESET} View status")
        print(f"    {C_CYAN}8){C_RESET} Cleanup completed specs")
        print(f"    {C_CYAN}q){C_RESET} Quit")
        print()

        try:
            choice = input(f"  {C_BOLD}>{C_RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n  Bye!")
            break

        if choice == "q":
            print("  Bye!")
            break

        elif choice == "1":
            action_insights(project_dir)

        elif choice == "2":
            action_discover(project_dir)

        elif choice == "3":
            try:
                path = input(f"  {C_BOLD}Path to batch JSON file:{C_RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if path:
                action_create_from_file(project_dir, path)

        elif choice == "4":
            qa_too = prompt_yn("Also run QA after each build?", default=False)
            action_build_all(project_dir, run_qa=qa_too)

        elif choice == "5":
            if not specs:
                print(f"  {C_YELLOW}No specs found.{C_RESET}")
                continue
            spec_options = [
                (f"{s['id']} — {s['title'][:50]}", STATUS_LABELS.get(s["status"], s["status"]))
                for s in specs
            ]
            sel = prompt_choice("Which spec to build?", spec_options)
            if sel:
                s = specs[sel[0]]
                qa_too = prompt_yn("Run QA after build?", default=False)
                action_build_spec(project_dir, s["id"], run_qa=qa_too)

        elif choice == "6":
            action_qa_all(project_dir)

        elif choice == "7":
            # Just loops back to top which shows status
            pass

        elif choice == "8":
            print()
            action_cleanup(project_dir, confirm=False)
            print()
            if prompt_yn("Proceed with cleanup?", default=False):
                action_cleanup(project_dir, confirm=True)

        else:
            print(f"  {C_DIM}Unknown option. Try 1-8 or q.{C_RESET}")

        print()


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Interactive batch task manager for Auto-Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ac-batch                            Interactive menu
  ac-batch --insights                 Interactive codebase Q&A chat
  ac-batch --insights "How does auth work?"   One-shot question
  ac-batch --status                   Show all spec statuses
  ac-batch --create tasks.json        Create specs from batch JSON
  ac-batch --discover                 Create batch from discovery outputs
  ac-batch --build                    Build all pending specs
  ac-batch --build --spec 016         Build specific spec
  ac-batch --build --qa               Build all + run QA
  ac-batch --qa                       QA all built specs
  ac-batch --cleanup                  Show cleanup preview
  ac-batch --cleanup --confirm        Actually clean up
        """,
    )
    parser.add_argument("--project-dir", type=Path, default=None,
                        help="Project directory (default: auto-detect from cwd)")
    parser.add_argument("--insights", nargs="?", const="", metavar="QUESTION",
                        help="Ask about the codebase (interactive if no question given)")
    parser.add_argument("--status", action="store_true",
                        help="Show status of all specs")
    parser.add_argument("--create", metavar="FILE",
                        help="Create specs from batch JSON file")
    parser.add_argument("--discover", action="store_true",
                        help="Interactive batch creation from discovery outputs")
    parser.add_argument("--build", action="store_true",
                        help="Build specs (all pending by default)")
    parser.add_argument("--spec", metavar="ID",
                        help="Specific spec ID to build (with --build)")
    parser.add_argument("--qa", action="store_true",
                        help="Run QA (on all built specs, or after --build)")
    parser.add_argument("--cleanup", action="store_true",
                        help="Clean up completed specs")
    parser.add_argument("--confirm", action="store_true",
                        help="Actually perform cleanup (with --cleanup)")

    args = parser.parse_args()

    # Find project
    if args.project_dir:
        project_dir = args.project_dir.resolve()
    else:
        project_dir = find_project_dir()

    if not project_dir:
        print(f"  {C_RED}Error: No .auto-claude/ directory found.{C_RESET}")
        print("  Run from inside a project with Auto-Claude,")
        print("  or pass --project-dir /path/to/project")
        sys.exit(1)

    # Handle CLI modes
    if args.insights is not None:
        if args.insights:
            action_insights(project_dir, message=args.insights)
        else:
            action_insights(project_dir)
        return

    if args.status:
        specs = load_all_specs(project_dir)
        print_header(f"ac-batch — {project_dir.name}")
        print_status_table(specs)
        return

    if args.create:
        action_create_from_file(project_dir, args.create)
        return

    if args.discover:
        action_discover(project_dir)
        return

    if args.build:
        if args.spec:
            action_build_spec(project_dir, args.spec, run_qa=args.qa)
        else:
            action_build_all(project_dir, run_qa=args.qa)
        return

    if args.qa:
        action_qa_all(project_dir)
        return

    if args.cleanup:
        action_cleanup(project_dir, confirm=args.confirm)
        return

    # Default: interactive mode
    interactive(project_dir)


if __name__ == "__main__":
    main()
