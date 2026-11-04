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


def test_ask_covers_every_other_github_write_the_agents_could_run():
    # Rooms run in auto mode: a command that matches no rule runs with no card. The review found
    # these writes matched nothing, so "gh pr edit 12 --add-label accepted" landed without one.
    for rule in (
        "Bash(gh pr edit:*)",
        "Bash(gh pr create:*)",
        "Bash(gh pr ready:*)",
        "Bash(gh pr reopen:*)",
        "Bash(gh issue create:*)",
        "Bash(gh issue reopen:*)",
        "Bash(gh issue lock:*)",
        "Bash(gh issue unlock:*)",
        "Bash(gh issue pin:*)",
        "Bash(gh issue unpin:*)",
        "Bash(gh issue transfer:*)",
        "Bash(gh issue develop:*)",
        "Bash(gh release:*)",
        "Bash(gh workflow:*)",
        "Bash(gh run:*)",
    ):
        assert rule in REQUIRED_ASK, rule


def test_ask_covers_interpreters_that_could_run_a_gh_write_without_a_card():
    # "python3 -c 'subprocess.run([\"gh\", ...])'" matches no gh rule; asking makes it raise a card.
    for rule in ("Bash(python:*)", "Bash(python3:*)", "Bash(node:*)", "Bash(bash:*)", "Bash(sh:*)", "Bash(zsh:*)"):
        assert rule in REQUIRED_ASK, rule


def test_deny_covers_account_repo_and_alias_commands_the_agents_never_need():
    for rule in (
        "Bash(gh alias:*)",
        "Bash(gh extension:*)",
        "Bash(gh auth:*)",
        "Bash(gh config:*)",
        "Bash(gh repo:*)",
        "Bash(gh gist:*)",
        "Bash(gh secret:*)",
        "Bash(gh variable:*)",
        "Bash(gh issue delete:*)",
    ):
        assert rule in REQUIRED_DENY, rule
