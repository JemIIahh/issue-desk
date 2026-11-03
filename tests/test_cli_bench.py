import subprocess
from pathlib import Path

import pytest
from fake_gh import comment_item, fake_gh, issue_raw, pr_item

from issue_desk import cli
from issue_desk.cli import DEFAULT_WORK_ROOT, main

ROOT = Path(__file__).resolve().parent.parent


def git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def commit_file(cwd, path, text, message):
    target = Path(cwd) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    git(cwd, "add", ".")
    git(cwd, "commit", "-q", "-m", message)


@pytest.fixture
def clone(tmp_path):
    """A clone whose origin has `pull/7/head` (source + test) and `pull/8/head` (README only)."""
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    commit_file(origin, "src/a.py", "x = 1\n", "base")
    for number, path in ((7, "src/a.py"), (8, "README.md")):
        git(origin, "checkout", "-q", "-b", f"b{number}", "main")
        commit_file(origin, path, f"change {number}\n", f"pr {number}")
        if number == 7:
            commit_file(origin, "tests/test_a.py", "def test_a(): pass\n", "add a test")
        git(origin, "update-ref", f"refs/pull/{number}/head", "HEAD")
        git(origin, "checkout", "-q", "main")
    target = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(origin), str(target))
    return target


@pytest.fixture
def work(tmp_path):
    return tmp_path / "work"


def routes(*, commenters=("alice",)):
    comments = [comment_item(login, "I would like to take this one.") for login in commenters]
    return {
        "repos/o/r/pulls": [
            [
                pr_item(7, "Backup", "Closes #5", login="alice"),
                pr_item(8, "Docs", "Fixes #5", login="mallory"),
                pr_item(9, "Elsewhere", "Closes #6", login="carol"),
            ]
        ],
        "repos/o/r/issues/5/comments": [comments],
        "repos/o/r/issues/5": [issue_raw(5)],
        "repos/o/r": {"default_branch": "main"},  # keep last: routes match by prefix
    }


@pytest.fixture
def fake_tests(monkeypatch):
    calls = []

    def fake(worktree, image, install_cmd, test_cmd, timeout=300):
        calls.append({"worktree": Path(worktree), "image": image, "install": install_cmd, "test": test_cmd})
        if Path(worktree).name == "pr-8":
            return "fail", "boom", ("blocked network attempt",)
        return "pass", "ok", ()

    monkeypatch.setattr(cli, "run_tests", fake)
    fake.calls = calls
    return fake


def bench(clone, work, *extra, run=None):
    argv = [
        "bench", "o/r", "5", "--repo-dir", str(clone), "--scope", "src/**", "--scope", "tests/**",
        "--test-cmd", "npm test", "--work-root", str(work), *extra,
    ]
    return main(argv, run=run or fake_gh(routes()))


def test_bench_compares_every_open_pr_that_closes_the_issue(capsys, clone, work, fake_tests):
    assert bench(clone, work) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "| PR | Author | Files (+/−) | Tests | Out of scope | Flags |"
    assert "| #7 |" in out and "| #8 |" in out
    assert "#9" not in out  # closes a different issue
    assert "✅ pass" in out and "❌ fail" in out


def test_bench_reports_scope_and_risk_flags_per_pr(capsys, clone, work, fake_tests):
    bench(clone, work)
    rows = {line.split("|")[1].strip(): line for line in capsys.readouterr().out.splitlines() if line.startswith("| #")}
    assert "README.md" in rows["#8"] and "no tests changed" in rows["#8"]
    assert "blocked network attempt" in rows["#8"]  # the sealed box's hint is merged in
    assert "README.md" not in rows["#7"] and "no tests changed" not in rows["#7"]


def test_bench_never_shows_real_logins_and_matches_the_scorecard_pseudonyms(capsys, clone, work, fake_tests):
    run = fake_gh(routes(commenters=("alice",)))
    bench(clone, work, run=run)
    out = capsys.readouterr().out
    assert "alice" not in out and "mallory" not in out
    assert "| #7 | contributor-1 |" in out  # alice is the first commenter, so the scorecard calls her contributor-1
    assert "| #8 | contributor-2 |" in out  # not in the thread: numbered after the participants


def test_bench_hands_the_commands_to_the_sealed_runner(clone, work, fake_tests):
    bench(clone, work, "--install-cmd", "npm ci --ignore-scripts", "--image", "node:22-slim")
    assert {c["image"] for c in fake_tests.calls} == {"node:22-slim"}
    assert {c["install"] for c in fake_tests.calls} == {"npm ci --ignore-scripts"}
    assert {c["test"] for c in fake_tests.calls} == {"npm test"}


def test_bench_defaults_to_the_node_image_and_no_install(clone, work, fake_tests):
    bench(clone, work)
    assert {c["image"] for c in fake_tests.calls} == {"node:20-slim"}
    assert {c["install"] for c in fake_tests.calls} == {None}


def test_bench_checks_each_pr_out_in_its_own_worktree_under_the_work_root(clone, work, fake_tests):
    bench(clone, work)
    assert sorted(c["worktree"] for c in fake_tests.calls) == [work / "pr-7", work / "pr-8"]
    assert (work / "pr-7" / "tests" / "test_a.py").exists()


def test_the_default_work_root_is_outside_the_agent_folders():
    # A PR's CLAUDE.md or .claude/ must never sit under a folder an agent works in.
    assert DEFAULT_WORK_ROOT == Path.home() / ".cache" / "issue-desk" / "work"
    assert not DEFAULT_WORK_ROOT.is_relative_to(ROOT)


def test_bench_with_no_matching_pr_says_so_and_exits_0(capsys, clone, work, fake_tests):
    only_other = {**routes(), "repos/o/r/pulls": [[pr_item(9, "Elsewhere", "Closes #6")]]}
    assert bench(clone, work, run=fake_gh(only_other)) == 0
    assert "No open pull requests close #5" in capsys.readouterr().out
    assert fake_tests.calls == []


def test_bench_finds_the_base_from_the_repos_default_branch_when_the_clone_has_no_origin_head(capsys, clone, work, fake_tests):
    # A clone made with `git init` + `git remote add` has no origin/HEAD; the default branch comes from GitHub.
    subprocess.run(["git", "-C", str(clone), "remote", "set-head", "origin", "-d"], check=True, capture_output=True)
    assert bench(clone, work) == 0
    assert "| #7 |" in capsys.readouterr().out


def test_bench_refuses_a_base_that_git_would_read_as_an_option(capsys, clone, work, fake_tests):
    assert bench(clone, work, "--base=--output=/tmp/should-not-exist") == 1
    assert "base" in capsys.readouterr().err
    assert fake_tests.calls == []


def test_bench_requires_the_scope_the_repo_dir_and_the_test_command(clone):
    for missing in (["--scope", "src/**", "--test-cmd", "t"], ["--repo-dir", str(clone), "--test-cmd", "t"], ["--repo-dir", str(clone), "--scope", "s"]):
        with pytest.raises(SystemExit) as exc:
            main(["bench", "o/r", "5", *missing], run=fake_gh({}))
        assert exc.value.code == 2


def docker_image_ready(image="python:3.12-slim"):
    try:
        return subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.mark.docker
@pytest.mark.skipif(not docker_image_ready(), reason="needs Docker and the python:3.12-slim image already pulled")
def test_bench_runs_the_real_sealed_box(capsys, clone, work):
    # A test command that needs no install and no network: it passes only where tests/test_a.py exists.
    argv = [
        "bench", "o/r", "5", "--repo-dir", str(clone), "--scope", "src/**", "--test-cmd",
        "python -c \"import sys; sys.exit(0 if __import__('pathlib').Path('tests/test_a.py').exists() else 1)\"",
        "--image", "python:3.12-slim", "--work-root", str(work),
    ]
    assert main(argv, run=fake_gh(routes())) == 0
    rows = {line.split("|")[1].strip(): line for line in capsys.readouterr().out.splitlines() if line.startswith("| #")}
    assert "✅ pass" in rows["#7"]  # the PR that added tests/test_a.py
    assert "❌ fail" in rows["#8"]  # the file is missing there
