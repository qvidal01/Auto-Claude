# Auto-Claude Quick Reference

## Aliases (add to ~/.zshrc)

```bash
alias ac-batch="python ~/projects/Auto-Claude/scripts/ac-batch.py"
alias ac-phase="python ~/projects/Auto-Claude/scripts/ac-phase.py"
```

## The Two Main Commands

| Command | Purpose |
|---------|---------|
| `ac-batch` | Interactive menu — discover, create specs, build |
| `ac-phase` | Execute specs in dependency-aware phases |

---

## Workflow 1: New Project / Full Analysis

```bash
cd ~/projects/my-app

# All-in-one interactive menu
ac-batch

# Or step by step:
ac-batch --insights                    # 1. Ask questions, understand the codebase
ac-batch --ideation                    # 2. Brainstorm improvements, bugs, security
ac-batch --roadmap                     # 3. Prioritize into strategic plan
ac-batch --discover                    # 4. Pick ideas → create specs
ac-phase                               # 5. Build specs in phased order
```

## Workflow 2: Quick Single Task

```bash
~/auto-claude.sh spec ~/projects/my-app --task "Add dark mode support"
~/auto-claude.sh run ~/projects/my-app --spec 001
```

## Workflow 3: Bug Fix / Issue Response

```bash
ac-batch --insights "What does this auth code do? Why might it break?"
~/auto-claude.sh github ~/projects/my-app triage
~/auto-claude.sh github ~/projects/my-app auto-fix 456
```

## Workflow 4: Ongoing Maintenance

```bash
ac-batch --ideation                    # Weekly scan
ac-batch --roadmap                     # Refresh priorities
ac-batch --discover                    # Create specs from findings
ac-phase                               # Build in order
~/auto-claude.sh worktrees ~/projects/my-app --cleanup
```

---

## ac-batch CLI Reference

```
Discover:
  ac-batch --insights                    Interactive codebase Q&A
  ac-batch --insights "question"         One-shot question
  ac-batch --ideation                    Brainstorm improvements
  ac-batch --roadmap                     Strategic feature roadmap

Create:
  ac-batch --discover                    Create specs from discovery outputs
  ac-batch --create tasks.json           Create specs from JSON file

Build:
  ac-batch --build                       Build all pending specs
  ac-batch --build --spec 003            Build specific spec
  ac-batch --build --qa                  Build all + run QA
  ac-batch --qa                          QA all built specs

Manage:
  ac-batch --status                      Show all spec statuses
  ac-batch --cleanup                     Preview cleanup
  ac-batch --cleanup --confirm           Delete completed specs
```

## ac-phase CLI Reference

```
  ac-phase                               Interactive menu
  ac-phase --status                      Show phase progress
  ac-phase --run                         Run next pending phase
  ac-phase --run --phase 2               Run specific phase
  ac-phase --run --all                   Run all remaining phases
  ac-phase --init                        Regenerate phases from specs
```

## auto-claude.sh Reference (individual commands)

```
  ~/auto-claude.sh ideation <path>              Brainstorm improvements
  ~/auto-claude.sh roadmap <path>               Create implementation roadmap
  ~/auto-claude.sh insights <path> "question"   Ask about the codebase
  ~/auto-claude.sh spec <path> --task "..."      Create spec for a task
  ~/auto-claude.sh run <path> --spec 001         Execute a spec build
  ~/auto-claude.sh github <path> review-pr 42    Review a PR
  ~/auto-claude.sh github <path> triage          Triage issues
  ~/auto-claude.sh github <path> auto-fix 456    Auto-fix an issue
  ~/auto-claude.sh list <path>                   List specs
  ~/auto-claude.sh worktrees <path> --cleanup    Clean up worktrees
  ~/auto-claude.sh ui                            Start desktop app
```

## Insights Example Questions

```bash
# Architecture
ac-batch --insights "What is the overall architecture?"
ac-batch --insights "How does authentication work?"

# Before changes
ac-batch --insights "What would I need to change to add a new feature?"
ac-batch --insights "What API endpoints exist?"

# Risk assessment
ac-batch --insights "Are there any security concerns or hardcoded credentials?"
ac-batch --insights "What are the biggest technical debt items?"

# Production readiness
ac-batch --insights "What features are missing for production readiness?"
ac-batch --insights "What error handling patterns are used?"
```

---

## Quick Mental Model

```
ac-batch = WHAT to build (discover → create → build)
ac-phase = HOW to build it (phased execution with review gates)
auto-claude.sh = individual commands for one-off tasks
```
