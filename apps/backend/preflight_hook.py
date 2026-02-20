"""Auto-Claude Preflight Hook.

Lightweight wrapper around preflight.py that runs checks before any runner.
Designed to be called once at the start of main() in each runner.

Usage in runners:
    from preflight_hook import run_preflight
    run_preflight()  # Returns True if OK, False if critical failure

Checks:
    - OAuth token present and not known-expired (auto-fixes from ~/.claude/.credentials.json)
    - Ollama reachable (warns but continues if down - only needed for local LLM tasks)
    - .env file exists

Skips checks if:
    - SKIP_PREFLIGHT=1 env var is set (for CI/testing)
    - Already ran this session (deduplication)
"""

import json
import logging
import os
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)

_preflight_ran = False
BACKEND_DIR = Path(__file__).parent
ENV_FILE = BACKEND_DIR / ".env"


def _load_env_vars() -> dict:
    """Read .env file into dict without importing dotenv."""
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip()
    return env


def _check_and_fix_token(env: dict) -> bool:
    """Check OAuth token, auto-fix from credentials if expired. Returns True if OK."""
    token = env.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not token:
        # Try auto-fix
        return _auto_fix_token()

    # Check for known-expired tokens (add patterns as discovered)
    known_expired = ["sk-ant-oat01-cnqsmZU"]
    for expired in known_expired:
        if token.startswith(expired):
            print("[preflight] OAuth token is known-expired, attempting auto-fix...")
            return _auto_fix_token()

    return True


def _auto_fix_token() -> bool:
    """Pull fresh token from ~/.claude/.credentials.json and update .env."""
    creds_file = Path.home() / ".claude" / ".credentials.json"
    if not creds_file.exists():
        print(
            "[preflight] ERROR: No OAuth token and ~/.claude/.credentials.json not found"
        )
        print("[preflight] Run 'claude /login' to authenticate, then try again")
        return False

    try:
        with open(creds_file) as f:
            creds = json.load(f)
        new_token = creds.get("claudeAiOauth", {}).get("accessToken", "")
        if not new_token:
            print("[preflight] ERROR: No access token in credentials file")
            return False

        # Update .env line-by-line to target only the token key
        content = ENV_FILE.read_text()
        lines = content.split("\n")
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith("CLAUDE_CODE_OAUTH_TOKEN="):
                lines[i] = f"CLAUDE_CODE_OAUTH_TOKEN={new_token}"
                updated = True
                break
        if not updated:
            lines.insert(0, f"CLAUDE_CODE_OAUTH_TOKEN={new_token}")

        ENV_FILE.write_text("\n".join(lines))
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = new_token
        print("[preflight] Token auto-fixed from ~/.claude/.credentials.json")
        return True
    except Exception as e:
        print(f"[preflight] Token auto-fix failed: {e}")
        return False


def _check_ollama(env: dict) -> bool:
    """Check Ollama connectivity. Warns but doesn't fail (not always needed)."""
    ollama_url = env.get("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        with urlopen(f"{ollama_url}/api/tags", timeout=3) as resp:
            resp.read()
        return True
    except (URLError, OSError):
        print(f"[preflight] WARNING: Ollama unreachable at {ollama_url}")
        print("[preflight]   Local LLM tasks (embeddings, complexity) may fail")
        return True  # Warn but don't block
    except Exception:
        print(f"[preflight] WARNING: Could not reach Ollama at {ollama_url}")
        return True  # Warn but don't block


def _check_stale_locks() -> None:
    """Remove stale .lock files from spec directories."""
    project_dirs = [Path.home() / "projects"]

    # Allow additional dirs via env var
    extra_dirs = os.environ.get("AUTO_CLAUDE_PROJECT_DIRS", "")
    if extra_dirs:
        for d in extra_dirs.split(":"):
            p = Path(d.strip())
            if p.exists():
                project_dirs.append(p)

    for pdir in project_dirs:
        if not pdir.exists():
            continue
        for lock_file in pdir.glob("*/.auto-claude/specs/*/.lock"):
            try:
                # Only remove locks older than 1 hour
                age = time.time() - lock_file.stat().st_mtime
                if age > 3600:
                    lock_file.unlink()
                    print(f"[preflight] Removed stale lock: {lock_file}")
            except OSError as e:
                logger.debug("Could not check/remove lock %s: %s", lock_file, e)


def run_preflight() -> bool:
    """Run preflight checks. Call at the start of each runner's main().

    Returns True if all critical checks pass.
    Raises SystemExit on critical failures since callers rely on early termination.
    """
    global _preflight_ran

    # Skip if already ran this process, or explicitly disabled
    if _preflight_ran:
        return True
    if os.environ.get("SKIP_PREFLIGHT") == "1":
        return True

    _preflight_ran = True

    # Check .env exists
    if not ENV_FILE.exists():
        print("[preflight] ERROR: .env file not found at", ENV_FILE)
        print("[preflight] Copy .env.example to .env and configure it")
        raise SystemExit(1)

    env = _load_env_vars()

    # Critical: OAuth token
    if not _check_and_fix_token(env):
        raise SystemExit(1)

    # Non-critical: Ollama
    _check_ollama(env)

    # Non-critical: Stale locks
    _check_stale_locks()

    return True
