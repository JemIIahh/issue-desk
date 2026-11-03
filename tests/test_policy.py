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
