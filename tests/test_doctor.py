import json
import shutil
import subprocess
from pathlib import Path

from triage_kit.gh import GhError

from issue_desk.cli import main
from issue_desk.doctor import Check, check_claude, check_docker, check_gh, check_mattermost, check_settings, run_doctor
from issue_desk.policy import AGENTS, REQUIRED_ASK

ROOT = Path(__file__).resolve().parent.parent


def gh_as(login):
    return lambda args: f"{login}\n"


def gh_fails(args):
    raise GhError("You are not logged into any GitHub hosts. Run gh auth login")


def cmd_ok(argv):
    return "27.4.0\n"


def cmd_missing(argv):
    raise FileNotFoundError(argv[0])


def test_gh_account_must_match_the_expected_one_and_the_detail_names_both():
    check = check_gh("JemIIahh", gh_as("Divine-designs"))
    assert not check.ok
    assert "Divine-designs" in check.detail and "JemIIahh" in check.detail


def test_gh_account_matches_ignoring_case_and_any_account_passes_when_none_is_expected():
    assert check_gh("jemiiahh", gh_as("JemIIahh")).ok
    assert check_gh(None, gh_as("anyone")).ok


def test_gh_not_logged_in_fails_and_says_how_to_fix_it():
    check = check_gh(None, gh_fails)
    assert not check.ok and "gh auth login" in check.detail


def test_docker_and_claude_checks_pass_with_a_version_and_fail_when_the_tool_is_missing():
    assert check_docker(cmd_ok).ok and check_claude(cmd_ok).ok
    assert not check_docker(cmd_missing).ok
    assert "claude" in check_claude(cmd_missing).detail.lower()
    failing = lambda argv: (_ for _ in ()).throw(subprocess.CalledProcessError(1, argv))  # noqa: E731
    assert not check_docker(failing).ok


def test_the_shipped_agent_settings_pass_for_every_agent():
    checks = check_settings(ROOT)
    assert [c.name for c in checks] == [f"{a} settings" for a in AGENTS]
    assert all(c.ok for c in checks), [c.detail for c in checks if not c.ok]


def test_a_settings_file_missing_one_ask_rule_fails_and_names_the_rule(tmp_path):
    shutil.copytree(ROOT / "agents", tmp_path / "agents")
    path = tmp_path / "agents" / "scout" / ".claude" / "settings.json"
    settings = json.loads(path.read_text())
    settings["permissions"]["ask"].remove(REQUIRED_ASK[0])
    path.write_text(json.dumps(settings))
    by_name = {c.name: c for c in check_settings(tmp_path)}
    assert not by_name["scout settings"].ok and REQUIRED_ASK[0] in by_name["scout settings"].detail
    assert by_name["desk settings"].ok


def test_a_missing_settings_file_fails(tmp_path):
    assert not any(c.ok for c in check_settings(tmp_path))


def test_mattermost_is_skipped_without_a_url_and_pings_the_system_endpoint_with_one():
    skipped = check_mattermost(None)
    assert skipped.ok and "skipped" in skipped.detail
    seen = []
    assert check_mattermost("http://localhost:8065/", lambda url: seen.append(url) or "OK").ok
    assert seen == ["http://localhost:8065/api/v4/system/ping"]
    assert not check_mattermost("http://localhost:1", lambda url: (_ for _ in ()).throw(OSError("refused"))).ok


def test_run_doctor_returns_1_when_any_check_fails_and_prints_a_mark_per_check(capsys):
    lines = []
    code = run_doctor(ROOT, "JemIIahh", None, gh=gh_as("Divine-designs"), cmd=cmd_ok, out=lines.append)
    assert code == 1
    assert any(line.startswith("✗ GitHub account") for line in lines)
    assert any(line.startswith("✓ Docker") for line in lines)


def test_run_doctor_returns_0_when_everything_passes():
    lines = []
    assert run_doctor(ROOT, None, None, gh=gh_as("anyone"), cmd=cmd_ok, out=lines.append) == 0
    assert all(line.startswith("✓") for line in lines)


def test_the_cli_runs_doctor_and_exits_1_on_the_wrong_account(capsys):
    assert main(["doctor", "--expect-account", "Somebody-else"], run=gh_as("JemIIahh")) == 1
    assert "✗ GitHub account" in capsys.readouterr().out


def test_check_is_a_plain_record():
    assert Check("a", True, "b") == Check(name="a", ok=True, detail="b")
