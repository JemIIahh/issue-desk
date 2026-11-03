"""`issue-desk doctor`: is everything in place before a rehearsal, so it does not fail halfway?"""

import json
import subprocess
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from triage_kit.gh import GhError, Runner, run_gh

from issue_desk.policy import AGENTS, missing_rules

Cmd = Callable[[list[str]], str]  # runs a full command line and returns its output
Getter = Callable[[str], str]  # fetches a URL and returns the body


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def run_cmd(argv: list[str]) -> str:
    return subprocess.run(argv, capture_output=True, text=True, check=True, timeout=30).stdout


def http_get(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"{url!r} is not an http(s) URL")
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 (scheme checked above)
        return response.read().decode(errors="replace")


def check_gh(expect: str | None = None, run: Runner = run_gh) -> Check:
    try:
        login = run(["api", "user", "--jq", ".login"]).strip()
    except (GhError, OSError) as err:
        return Check("GitHub account", False, f"gh is not ready ({err}). Run: gh auth login")
    if expect and login.lower() != expect.lower():
        return Check("GitHub account", False, f"logged in as {login}, expected {expect}. Run: gh auth switch")
    return Check("GitHub account", True, f"logged in as {login}")


def check_docker(run: Cmd = run_cmd) -> Check:
    try:
        version = run(["docker", "info", "--format", "{{.ServerVersion}}"]).strip()
    except (OSError, subprocess.SubprocessError):
        return Check("Docker", False, "not running or not installed; bench tests pull requests in a sealed container, so start Docker")
    return Check("Docker", True, f"running (server {version})")


def check_claude(run: Cmd = run_cmd) -> Check:
    try:
        version = run(["claude", "--version"]).strip()
    except (OSError, subprocess.SubprocessError):
        return Check("Claude Code", False, "`claude` not found; the three agents run on Claude Code, so install it first")
    return Check("Claude Code", True, version)


def check_settings(root: Path) -> list[Check]:
    """Every agent folder must carry the approval (ask) and deny rules that keep GitHub writes behind the card."""
    checks = []
    for agent in AGENTS:
        name = f"{agent} settings"
        path = root / "agents" / agent / ".claude" / "settings.json"
        try:
            settings = json.loads(path.read_text())
        except OSError:
            checks.append(Check(name, False, f"{path} not found"))
            continue
        except json.JSONDecodeError as err:
            checks.append(Check(name, False, f"{path} is not valid JSON ({err})"))
            continue
        missing = missing_rules(settings)
        checks.append(Check(name, not missing, "missing rules: " + ", ".join(missing) if missing else "approval and deny rules present"))
    return checks


def check_mattermost(url: str | None, get: Getter = http_get) -> Check:
    if url is None:
        return Check("Mattermost", True, "skipped (pass --mattermost URL to check it)")
    target = url.rstrip("/") + "/api/v4/system/ping"
    try:
        get(target)
    except (OSError, ValueError) as err:
        return Check("Mattermost", False, f"{target} did not answer ({err})")
    return Check("Mattermost", True, f"{url} answers")


def run_doctor(
    root: Path,
    expect: str | None,
    mattermost_url: str | None,
    *,
    gh: Runner = run_gh,
    cmd: Cmd = run_cmd,
    get: Getter = http_get,
    out: Callable[[str], None] = print,
) -> int:
    """Print one line per check and return 1 if any failed."""
    checks = [check_gh(expect, gh), check_docker(cmd), check_claude(cmd), *check_settings(root), check_mattermost(mattermost_url, get)]
    for check in checks:
        out(f"{'✓' if check.ok else '✗'} {check.name} — {check.detail}")
    return 0 if all(c.ok for c in checks) else 1
