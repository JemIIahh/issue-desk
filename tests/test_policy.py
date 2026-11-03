import json
from pathlib import Path

from issue_desk.policy import AGENTS, REQUIRED_ASK, REQUIRED_DENY, missing_rules

ROOT = Path(__file__).resolve().parents[1]


def test_every_agent_settings_has_required_rules():
    for name in AGENTS:
        path = ROOT / "agents" / name / ".claude" / "settings.json"
        data = json.loads(path.read_text())
        assert missing_rules(data) == [], name


def test_missing_rules_reports_gaps():
    empty = {"permissions": {"ask": [], "deny": []}}
    assert missing_rules(empty) == list(REQUIRED_ASK) + list(REQUIRED_DENY)


def test_deny_covers_forms_the_plain_prefix_rules_miss():
    # "Bash(git push:*)" does not match "git -C . push" or "git -c k=v push", and the
    # maintainer-only commands can be run without "uv run", so those forms are denied too.
    for rule in (
        "Bash(git -C:*)",
        "Bash(git -c:*)",
        "Bash(issue-desk mirror:*)",
        "Bash(issue-desk seed-practice:*)",
        "Bash(python -m issue_desk:*)",
        "Bash(uv run python -m issue_desk:*)",
    ):
        assert rule in REQUIRED_DENY, rule
