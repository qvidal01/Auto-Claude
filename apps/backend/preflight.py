#!/usr/bin/env python3
"""Auto-Claude Preflight Check & Self-Healing Script.

Run before any Auto-Claude command to detect and fix common issues.
Usage: python preflight.py [--fix]
"""
import json
import os
import sys
import subprocess
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
ENV_FILE = BACKEND_DIR / ".env"
VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")

def warn(msg):
    print(f"  {YELLOW}⚠{RESET} {msg}")

def fail(msg):
    print(f"  {RED}✗{RESET} {msg}")

def info(msg):
    print(f"  {BLUE}ℹ{RESET} {msg}")


class PreflightCheck:
    def __init__(self, auto_fix=False):
        self.auto_fix = auto_fix
        self.issues = []
        self.fixed = []

    def check_env_file(self):
        """Verify .env exists and has required fields."""
        print(f"\n{BLUE}[1/6] Checking .env configuration{RESET}")
        if not ENV_FILE.exists():
            fail(".env file not found")
            self.issues.append("missing_env")
            return

        env = {}
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()

        # Check OAuth token
        token = env.get("CLAUDE_CODE_OAUTH_TOKEN", "")
        if not token or token.startswith("sk-ant-oat01-cnqsmZU"):
            fail("OAuth token missing or known-expired")
            self.issues.append("expired_token")
            if self.auto_fix:
                self._fix_token(env)
        else:
            ok(f"OAuth token present ({token[:20]}...)")

        # Check Ollama URL
        ollama_url = env.get("OLLAMA_BASE_URL", "")
        if not ollama_url:
            fail("OLLAMA_BASE_URL not set")
            self.issues.append("missing_ollama_url")
        else:
            ok(f"Ollama URL: {ollama_url}")

        # Check required providers
        for key in ["GRAPHITI_LLM_PROVIDER", "GRAPHITI_EMBEDDER_PROVIDER"]:
            if key in env:
                ok(f"{key}={env[key]}")
            else:
                warn(f"{key} not set")

    def _fix_token(self, env):
        """Auto-fix expired OAuth token from ~/.claude/.credentials.json."""
        creds_file = Path.home() / ".claude" / ".credentials.json"
        if not creds_file.exists():
            fail("Cannot auto-fix: ~/.claude/.credentials.json not found")
            return

        try:
            with open(creds_file) as f:
                creds = json.load(f)
            new_token = creds.get("claudeAiOauth", {}).get("accessToken", "")
            if not new_token:
                fail("No access token in credentials file")
                return

            # Read and update .env
            content = ENV_FILE.read_text()
            old_token = env.get("CLAUDE_CODE_OAUTH_TOKEN", "")
            if old_token:
                content = content.replace(old_token, new_token)
            else:
                content = f"CLAUDE_CODE_OAUTH_TOKEN={new_token}\n" + content
            ENV_FILE.write_text(content)
            ok(f"Token auto-fixed from ~/.claude/.credentials.json ({new_token[:20]}...)")
            self.fixed.append("expired_token")
        except Exception as e:
            fail(f"Auto-fix failed: {e}")

    def check_ollama(self):
        """Verify Ollama is reachable and models are available."""
        print(f"\n{BLUE}[2/6] Checking Ollama connectivity{RESET}")

        # Read URL from .env
        ollama_url = "http://192.168.0.234:11434"
        if ENV_FILE.exists():
            with open(ENV_FILE) as f:
                for line in f:
                    if line.strip().startswith("OLLAMA_BASE_URL="):
                        ollama_url = line.strip().split("=", 1)[1]

        try:
            result = subprocess.run(
                ["curl", "-s", "-m", "5", f"{ollama_url}/api/tags"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                fail(f"Ollama unreachable at {ollama_url}")
                self.issues.append("ollama_unreachable")
                return

            data = json.loads(result.stdout)
            models = [m["name"] for m in data.get("models", [])]
            ok(f"Ollama responding ({len(models)} models)")

            # Check required models
            required = ["qwen2.5-coder:14b", "nomic-embed-text"]
            for model in required:
                found = any(model in m for m in models)
                if found:
                    ok(f"Model available: {model}")
                else:
                    fail(f"Model missing: {model}")
                    self.issues.append(f"missing_model_{model}")
        except Exception as e:
            fail(f"Ollama check failed: {e}")
            self.issues.append("ollama_error")

    def check_venv(self):
        """Verify Python venv and dependencies."""
        print(f"\n{BLUE}[3/6] Checking Python environment{RESET}")
        if not VENV_PYTHON.exists():
            fail(f"venv not found at {VENV_PYTHON}")
            self.issues.append("missing_venv")
            if self.auto_fix:
                info("Run: cd apps/backend && python3 -m venv .venv && pip install -r requirements.txt")
            return

        ok(f"venv exists at {VENV_PYTHON}")

        # Check key imports
        try:
            result = subprocess.run(
                [str(VENV_PYTHON), "-c", "from core.client import create_client; print('OK')"],
                capture_output=True, text=True, timeout=10, cwd=str(BACKEND_DIR)
            )
            if "OK" in result.stdout:
                ok("Core imports working")
            else:
                fail(f"Import error: {result.stderr[:100]}")
                self.issues.append("import_error")
        except Exception as e:
            fail(f"venv check failed: {e}")

    def check_stuck_specs(self):
        """Find and optionally clear stuck specs/locks."""
        print(f"\n{BLUE}[4/6] Checking for stuck specs/locks{RESET}")

        # Check common project locations
        project_dirs = [
            Path.home() / "projects",
            Path("/aidata/projects"),
        ]

        stuck_count = 0
        for pdir in project_dirs:
            if not pdir.exists():
                continue
            for spec_dir in pdir.glob("*/.auto-claude/specs/*/.state"):
                stuck_count += 1
                warn(f"State cache: {spec_dir}")

            for lock_file in pdir.glob("*/.auto-claude/specs/*/.lock"):
                stuck_count += 1
                warn(f"Lock file: {lock_file}")
                if self.auto_fix:
                    lock_file.unlink()
                    ok(f"Removed stale lock: {lock_file}")
                    self.fixed.append(f"lock_{lock_file.name}")

        if stuck_count == 0:
            ok("No stuck specs or locks found")
        else:
            info(f"Found {stuck_count} items (use --fix to clean)")

    def check_node(self):
        """Verify Node.js version for Claude Code."""
        print(f"\n{BLUE}[5/6] Checking Node.js{RESET}")
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            version = result.stdout.strip()
            major = int(version.lstrip("v").split(".")[0])
            if major >= 24:
                ok(f"Node.js {version}")
            else:
                warn(f"Node.js {version} - Auto-Claude needs v24+")
                self.issues.append("old_node")
        except Exception:
            warn("Node.js not found in PATH")

    def check_git_status(self):
        """Check for uncommitted Auto-Claude changes in projects."""
        print(f"\n{BLUE}[6/6] Checking git status{RESET}")
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"], capture_output=True, text=True,
                timeout=5, cwd=str(BACKEND_DIR)
            )
            if result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                warn(f"Auto-Claude repo has {len(lines)} uncommitted changes")
            else:
                ok("Auto-Claude repo clean")
        except Exception:
            warn("Could not check git status")

    def run(self):
        print(f"\n{'='*60}")
        print(f" Auto-Claude Preflight Check {'(+ Auto-Fix)' if self.auto_fix else ''}")
        print(f"{'='*60}")

        self.check_env_file()
        self.check_ollama()
        self.check_venv()
        self.check_stuck_specs()
        self.check_node()
        self.check_git_status()

        # Summary
        print(f"\n{'='*60}")
        if not self.issues:
            print(f" {GREEN}All checks passed! Auto-Claude is ready.{RESET}")
        else:
            print(f" {YELLOW}{len(self.issues)} issue(s) found", end="")
            if self.fixed:
                print(f", {len(self.fixed)} auto-fixed", end="")
            print(f"{RESET}")
            remaining = [i for i in self.issues if i not in self.fixed]
            if remaining:
                print(f" {RED}Remaining: {', '.join(remaining)}{RESET}")
                if not self.auto_fix:
                    print(f"\n Run with --fix to attempt auto-repair")
        print(f"{'='*60}\n")

        return len(self.issues) - len(self.fixed) == 0


if __name__ == "__main__":
    auto_fix = "--fix" in sys.argv
    checker = PreflightCheck(auto_fix=auto_fix)
    success = checker.run()
    sys.exit(0 if success else 1)
