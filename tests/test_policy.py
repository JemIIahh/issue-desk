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


def test_deny_covers_the_flag_before_the_subcommand_forms():
    # `gh pr -R owner/repo merge 7` is valid gh and does not start with "gh pr merge".
    for group in ("pr", "issue", "release", "run", "workflow", "label"):
        for flag in ("-R", "--repo"):
            assert f"Bash(gh {group} {flag}:*)" in REQUIRED_DENY, (group, flag)


def test_deny_covers_pr_commands_that_push_or_run_pr_code_and_groups_the_agents_never_need():
    for rule in (
        "Bash(gh pr update-branch:*)",  # pushes to the contributor's branch
        "Bash(gh pr checkout:*)",  # puts the PR's code on the host; only `issue-desk bench` may run it
        "Bash(gh cache:*)",
        "Bash(gh project:*)",
        "Bash(gh ruleset:*)",
        "Bash(gh codespace:*)",
        "Bash(gh org:*)",
        "Bash(gh ssh-key:*)",
        "Bash(gh gpg-key:*)",
    ):
        assert rule in REQUIRED_DENY, rule
    for rule in ("Bash(gh pr lock:*)", "Bash(gh pr unlock:*)", "Bash(gh pr revert:*)"):
        assert rule in REQUIRED_ASK, rule


def test_ask_covers_wrappers_and_git_commands_that_bring_a_prs_code_onto_the_host():
    # `env gh pr merge 7` starts with "env", not "gh"; `git fetch origin pull/7/head && git checkout` puts PR code on the host.
    for rule in (
        "Bash(env:*)", "Bash(command:*)", "Bash(xargs:*)", "Bash(timeout:*)", "Bash(nohup:*)", "Bash(exec:*)", "Bash(sudo:*)",
        "Bash(git fetch:*)", "Bash(git checkout:*)", "Bash(git switch:*)", "Bash(git worktree:*)",
        "Bash(git apply:*)", "Bash(git am:*)", "Bash(git pull:*)",
    ):
        assert rule in REQUIRED_ASK, rule


def test_deny_covers_git_global_flags_that_hide_the_subcommand():
    for rule in ("Bash(git --git-dir:*)", "Bash(git --work-tree:*)", "Bash(git --no-pager:*)", "Bash(git -P:*)"):
        assert rule in REQUIRED_DENY, rule


def test_deny_covers_every_git_global_option_that_takes_effect_before_the_subcommand():
    # git's documented global options as of git 2.4x. A later git release can add one, so this is a best-effort
    # list, not a proof of completeness.
    for flag in (
        "-C", "-c", "-p", "-P", "--paginate", "--no-pager", "--bare", "--git-dir", "--work-tree", "--namespace",
        "--exec-path", "--config-env", "--super-prefix", "--no-replace-objects", "--no-lazy-fetch",
        "--no-optional-locks", "--no-advice", "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs",
        "--icase-pathspecs", "--attr-source",
    ):
        assert f"Bash(git {flag}:*)" in REQUIRED_DENY, flag
