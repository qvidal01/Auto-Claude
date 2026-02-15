#!/usr/bin/env python3
"""
Auto-Claude: Interactive Batch Task Creator
============================================
Reads ideation, roadmap, or insights output from any project's
.auto-claude/ directory and walks you through creating batch specs.

Usage:
  python batch-from-discovery.py                      # auto-detect project (cwd)
  python batch-from-discovery.py /path/to/project     # specify project
  python batch-from-discovery.py --auto-claude-dir /path/to/Auto-Claude  # custom AC path
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def header(text):
    try:
        width = min(os.get_terminal_size().columns, 72)
    except OSError:
        width = 72
    print(f"\n{CYAN}{'═' * width}{RESET}")
    print(f"{CYAN}{BOLD}  {text}{RESET}")
    print(f"{CYAN}{'═' * width}{RESET}\n")


def subheader(text):
    print(f"\n{BLUE}{BOLD}  ▸ {text}{RESET}\n")


def success(text):
    print(f"  {GREEN}✓{RESET} {text}")


def warn(text):
    print(f"  {YELLOW}⚠{RESET} {text}")


def error(text):
    print(f"  {RED}✗{RESET} {text}")


def info(text):
    print(f"  {DIM}→{RESET} {text}")


def prompt_choice(question, options, allow_multi=False, allow_all=True):
    """Interactive numbered menu. Returns list of selected indices."""
    print(f"  {BOLD}{question}{RESET}")
    print()
    for i, (label, detail) in enumerate(options, 1):
        detail_str = f" {DIM}— {detail}{RESET}" if detail else ""
        print(f"    {CYAN}{i:>3}{RESET}) {label}{detail_str}")

    if allow_all:
        print(f"    {CYAN}  a{RESET}) All of the above")
    print(f"    {CYAN}  q{RESET}) Cancel / go back")
    print()

    while True:
        raw = input(f"  {BOLD}>{RESET} ").strip().lower()
        if raw == "q":
            return []
        if raw == "a" and allow_all:
            return list(range(len(options)))
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
        warn("Invalid choice. Enter a number, 'a' for all, or 'q' to cancel.")


def prompt_yn(question, default=True):
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {BOLD}{question}{RESET} [{hint}] ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------

def detect_sources(project_dir: Path):
    """Scan .auto-claude/ for available discovery outputs."""
    ac_dir = project_dir / ".auto-claude"
    sources = []

    # Ideation
    ideation_file = ac_dir / "ideation" / "ideation.json"
    if ideation_file.exists():
        try:
            data = json.loads(ideation_file.read_text())
            count = len(data.get("ideas", []))
            sources.append({
                "type": "ideation",
                "file": ideation_file,
                "data": data,
                "count": count,
                "label": f"Ideation ({count} ideas)",
            })
        except (json.JSONDecodeError, KeyError):
            pass

    # Roadmap
    roadmap_file = ac_dir / "roadmap" / "roadmap.json"
    if roadmap_file.exists():
        try:
            data = json.loads(roadmap_file.read_text())
            count = len(data.get("features", []))
            sources.append({
                "type": "roadmap",
                "file": roadmap_file,
                "data": data,
                "count": count,
                "label": f"Roadmap ({count} features)",
            })
        except (json.JSONDecodeError, KeyError):
            pass

    # Insights — check for saved chat messages with suggestedTasks
    insights_dir = ac_dir / "insights"
    if insights_dir.exists():
        tasks = _collect_insights_tasks(insights_dir)
        if tasks:
            sources.append({
                "type": "insights",
                "file": insights_dir,
                "data": {"tasks": tasks},
                "count": len(tasks),
                "label": f"Insights ({len(tasks)} suggested tasks)",
            })

    return sources


def _collect_insights_tasks(insights_dir: Path):
    """Collect task suggestions from insights output files."""
    tasks = []
    for f in sorted(insights_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            # Could be a chat messages file or a direct suggestions file
            if isinstance(data, list):
                for msg in data:
                    for t in msg.get("suggestedTasks", []):
                        if t.get("title"):
                            tasks.append(t)
            elif isinstance(data, dict):
                for t in data.get("suggestedTasks", data.get("tasks", [])):
                    if isinstance(t, dict) and t.get("title"):
                        tasks.append(t)
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return tasks


# ---------------------------------------------------------------------------
# Item extraction (normalize all sources to common format)
# ---------------------------------------------------------------------------

def extract_items(source):
    """Return list of normalized items from any source type."""
    src_type = source["type"]
    data = source["data"]

    if src_type == "ideation":
        return [_normalize_ideation_idea(i) for i in data.get("ideas", [])]
    elif src_type == "roadmap":
        return [_normalize_roadmap_feature(f, data) for f in data.get("features", [])]
    elif src_type == "insights":
        return [_normalize_insights_task(t) for t in data.get("tasks", [])]
    return []


def _normalize_ideation_idea(idea):
    effort = (idea.get("estimated_effort") or idea.get("estimatedEffort", "medium")).lower()
    severity = idea.get("severity", "")

    # Build rich description
    parts = [idea.get("description", "")]
    if idea.get("rationale"):
        parts.append(f"\nRationale: {idea['rationale']}")
    if idea.get("implementation_approach"):
        parts.append(f"\nApproach: {idea['implementation_approach']}")
    if idea.get("implementation"):
        parts.append(f"\nImplementation: {idea['implementation']}")
    if idea.get("remediation"):
        parts.append(f"\nRemediation: {idea['remediation']}")
    if idea.get("proposedChange"):
        parts.append(f"\nProposed change: {idea['proposedChange']}")
    files = idea.get("affected_files") or idea.get("affectedFiles") or idea.get("affectedAreas", [])
    if files:
        parts.append(f"\nAffected files: {', '.join(files)}")

    return {
        "id": idea.get("id", "?"),
        "title": idea.get("title", "Untitled"),
        "description": "\n".join(parts),
        "category": idea.get("type", "general"),
        "effort": effort,
        "severity": severity,
        "source": "ideation",
    }


def _normalize_roadmap_feature(feature, roadmap_data):
    phases = {p["id"]: p.get("name", p["id"]) for p in roadmap_data.get("phases", [])}
    phase_name = phases.get(feature.get("phase_id", ""), "")

    parts = [feature.get("description", "")]
    if feature.get("rationale"):
        parts.append(f"\nRationale: {feature['rationale']}")
    if feature.get("acceptance_criteria"):
        criteria = "\n".join(f"  - {c}" for c in feature["acceptance_criteria"])
        parts.append(f"\nAcceptance criteria:\n{criteria}")
    if feature.get("user_stories"):
        stories = "\n".join(f"  - {s}" for s in feature["user_stories"])
        parts.append(f"\nUser stories:\n{stories}")

    complexity = feature.get("complexity", "medium").lower()
    effort_map = {"low": "small", "medium": "medium", "high": "large"}

    return {
        "id": feature.get("id", "?"),
        "title": feature.get("title", "Untitled"),
        "description": "\n".join(parts),
        "category": f"roadmap/{phase_name}" if phase_name else "roadmap",
        "effort": effort_map.get(complexity, "medium"),
        "severity": "",
        "priority_label": feature.get("priority", ""),
        "source": "roadmap",
    }


def _normalize_insights_task(task):
    meta = task.get("metadata", {})
    return {
        "id": meta.get("category", "insight"),
        "title": task.get("title", "Untitled"),
        "description": task.get("description", ""),
        "category": meta.get("category", "general"),
        "effort": meta.get("complexity", "medium"),
        "severity": meta.get("impact", ""),
        "source": "insights",
    }


# ---------------------------------------------------------------------------
# Filtering UI
# ---------------------------------------------------------------------------

EFFORT_ORDER = ["trivial", "small", "medium", "large", "high", "complex"]


def filter_items_interactive(items):
    """Walk user through filtering items. Returns filtered list."""
    if not items:
        return items

    # Show summary by category
    categories = {}
    for item in items:
        cat = item["category"]
        categories.setdefault(cat, []).append(item)

    subheader("Available categories")
    cat_options = []
    for cat, cat_items in sorted(categories.items()):
        efforts = [i["effort"] for i in cat_items]
        effort_summary = ", ".join(f"{e}:{efforts.count(e)}" for e in dict.fromkeys(efforts))
        cat_options.append((f"{cat} ({len(cat_items)} items)", effort_summary))

    selected_cats = prompt_choice(
        "Which categories do you want to include?",
        cat_options,
        allow_multi=True,
    )
    if not selected_cats:
        return []

    cat_keys = list(sorted(categories.keys()))
    chosen_cats = {cat_keys[i] for i in selected_cats}
    filtered = [item for item in items if item["category"] in chosen_cats]
    info(f"{len(filtered)} items selected")

    # Filter by effort?
    if prompt_yn("Filter by max effort level?", default=False):
        effort_options = [(e, "") for e in EFFORT_ORDER]
        sel = prompt_choice("Max effort to include:", effort_options, allow_all=False)
        if sel:
            max_idx = sel[0]
            allowed_efforts = set(EFFORT_ORDER[: max_idx + 1])
            filtered = [i for i in filtered if i["effort"] in allowed_efforts]
            info(f"{len(filtered)} items after effort filter")

    # Cherry-pick individual items?
    if len(filtered) > 1 and prompt_yn("Cherry-pick individual items?", default=False):
        item_options = [
            (f"[{i['id']}] {i['title']}", f"{i['effort']} effort")
            for i in filtered
        ]
        sel = prompt_choice("Select items:", item_options, allow_multi=True)
        if not sel:
            return []
        filtered = [filtered[i] for i in sel]

    return filtered


# ---------------------------------------------------------------------------
# Batch task conversion
# ---------------------------------------------------------------------------

TYPE_TO_WORKFLOW = {
    "code_improvements": "feature",
    "ui_ux_improvements": "feature",
    "documentation_gaps": "documentation",
    "security_hardening": "bugfix",
    "performance_optimizations": "feature",
    "code_quality": "refactor",
    "feature": "feature",
    "bug_fix": "bugfix",
    "refactoring": "refactor",
    "documentation": "documentation",
    "security": "bugfix",
    "performance": "feature",
    "ui_ux": "feature",
    "infrastructure": "feature",
    "testing": "feature",
}

EFFORT_TO_PRIORITY = {
    "trivial": 1,
    "small": 3,
    "medium": 5,
    "large": 7,
    "high": 7,
    "complex": 9,
}

EFFORT_TO_HOURS = {
    "trivial": 1,
    "small": 2,
    "medium": 4,
    "large": 8,
    "high": 8,
    "complex": 16,
}


def item_to_batch_task(item):
    effort = item.get("effort", "medium")
    cat = item.get("category", "general").split("/")[0]  # strip roadmap/phase prefix

    return {
        "title": f"[{item['id']}] {item['title']}",
        "description": item["description"],
        "workflow_type": TYPE_TO_WORKFLOW.get(cat, "feature"),
        "services": ["frontend"],
        "priority": EFFORT_TO_PRIORITY.get(effort, 5),
        "complexity": "quick" if effort in ("trivial", "small") else "standard",
        "estimated_hours": EFFORT_TO_HOURS.get(effort, 4),
    }


# ---------------------------------------------------------------------------
# Main interactive flow
# ---------------------------------------------------------------------------

def find_auto_claude_dir():
    """Try to find the Auto-Claude installation."""
    candidates = [
        Path("/aidata/projects/Auto-Claude"),
        Path.home() / "Auto-Claude",
        Path.home() / "auto-claude",
    ]
    # Also check if we're inside Auto-Claude itself
    cwd = Path.cwd()
    if (cwd / "apps" / "backend" / "run.py").exists():
        candidates.insert(0, cwd)

    for p in candidates:
        if (p / "apps" / "backend" / "run.py").exists():
            return p
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Interactive batch task creator from Auto-Claude discovery outputs"
    )
    parser.add_argument("project", nargs="?", default=".", help="Project directory (default: cwd)")
    parser.add_argument("--auto-claude-dir", help="Path to Auto-Claude installation")
    parser.add_argument("--dry-run", action="store_true", help="Generate batch file but don't run batch-create")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    if not project_dir.exists():
        error(f"Project directory not found: {project_dir}")
        sys.exit(1)

    ac_dir = Path(args.auto_claude_dir) if args.auto_claude_dir else find_auto_claude_dir()
    run_py = ac_dir / "apps" / "backend" / "run.py" if ac_dir else None

    # ── Welcome ──────────────────────────────────────────────────────
    clear_screen()
    header("Auto-Claude: Batch Task Creator")
    info(f"Project: {project_dir}")
    if ac_dir:
        info(f"Auto-Claude: {ac_dir}")
    else:
        warn("Auto-Claude installation not found — will generate batch file only")
    print()

    # ── Step 1: Detect sources ───────────────────────────────────────
    subheader("Step 1: Detecting discovery outputs")

    sources = detect_sources(project_dir)
    if not sources:
        error("No discovery outputs found in .auto-claude/")
        print()
        info("Run one of these first:")
        info("  python run.py --project . --ideation")
        info("  python run.py --project . --roadmap")
        info("  python run.py --project . --insights")
        sys.exit(1)

    for s in sources:
        success(f"{s['label']}  →  {s['file']}")

    # ── Step 2: Choose source ────────────────────────────────────────
    print()
    if len(sources) == 1:
        chosen_source = sources[0]
        info(f"Only one source found, using: {chosen_source['label']}")
    else:
        subheader("Step 2: Choose a source")
        src_options = [(s["label"], str(s["file"])) for s in sources]
        sel = prompt_choice("Which discovery output do you want to use?", src_options, allow_all=False)
        if not sel:
            info("Cancelled.")
            sys.exit(0)
        chosen_source = sources[sel[0]]

    success(f"Using: {chosen_source['label']}")

    # ── Step 3: Extract & display items ──────────────────────────────
    items = extract_items(chosen_source)
    if not items:
        error("No items found in this source.")
        sys.exit(1)

    subheader(f"Step 3: Review items ({len(items)} total)")
    print()
    for i, item in enumerate(items, 1):
        sev = f" {RED}[{item['severity']}]{RESET}" if item.get("severity") else ""
        print(f"    {DIM}{i:>3}.{RESET} [{item['id']}] {item['title']}{sev}")
        print(f"         {DIM}{item['category']} · {item['effort']} effort{RESET}")
    print()

    # ── Step 4: Filter ───────────────────────────────────────────────
    subheader("Step 4: Filter & select")
    filtered = filter_items_interactive(items)

    if not filtered:
        info("No items selected. Exiting.")
        sys.exit(0)

    print()
    success(f"{len(filtered)} items selected for batch creation:")
    print()
    for item in filtered:
        print(f"    • [{item['id']}] {item['title']} {DIM}({item['effort']}){RESET}")

    # ── Step 5: Confirm & generate ───────────────────────────────────
    print()
    if not prompt_yn(f"Generate batch file with {len(filtered)} tasks?"):
        info("Cancelled.")
        sys.exit(0)

    tasks = [item_to_batch_task(item) for item in filtered]
    batch = {"tasks": tasks}

    output_dir = project_dir / ".auto-claude" / "ideation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "batch_tasks.json"

    output_file.write_text(json.dumps(batch, indent=2))
    print()
    success(f"Batch file written: {output_file}")
    info(f"Contains {len(tasks)} tasks")

    # ── Step 6: Run batch-create ─────────────────────────────────────
    if args.dry_run or not run_py or not run_py.exists():
        print()
        subheader("Next step — run manually:")
        if run_py and run_py.exists():
            print(f"    python {run_py} \\")
        else:
            print(f"    python /path/to/Auto-Claude/apps/backend/run.py \\")
        print(f"      --project {project_dir} \\")
        print(f"      --batch-create {output_file}")
        print()
        print(f"    {DIM}Then build each spec:{RESET}")
        print(f"    python run.py --project {project_dir} --spec <NNN> --build")
        return

    print()
    if not prompt_yn("Run batch-create now to generate all specs?"):
        info("Batch file saved. You can run it later:")
        print(f"    python {run_py} --project {project_dir} --batch-create {output_file}")
        return

    subheader("Step 6: Creating specs")
    print()

    cmd = [
        sys.executable, str(run_py),
        "--project", str(project_dir),
        "--batch-create", str(output_file),
    ]

    result = subprocess.run(cmd, cwd=str(project_dir))

    if result.returncode == 0:
        print()
        success("Batch creation complete!")
        print()
        subheader("What's next?")
        print(f"    {BOLD}Check status:{RESET}")
        print(f"      python {run_py} --project {project_dir} --batch-status")
        print()
        print(f"    {BOLD}Generate full spec + build for a task:{RESET}")
        print(f"      python {run_py} --project {project_dir} --spec <NNN>")
        print(f"      python {run_py} --project {project_dir} --spec <NNN> --build")
        print()
        print(f"    {BOLD}QA validate:{RESET}")
        print(f"      python {run_py} --project {project_dir} --spec <NNN> --qa")
        print()
        print(f"    {BOLD}Clean up when done:{RESET}")
        print(f"      python {run_py} --project {project_dir} --batch-cleanup")
    else:
        error(f"Batch creation failed with exit code {result.returncode}")


if __name__ == "__main__":
    main()
