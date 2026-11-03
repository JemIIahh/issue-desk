import subprocess

import pytest
from fake_gh import comment_item, fake_gh, issue_raw

from issue_desk.cli import main

PLAN_A = (
    "I would change `core/x/loader.py` to read the manifest once, cache the parsed result, and add a regression test; "
    "I would also touch `core/y/gone.py` so that the retry path shares the same cache entry and the tests stay small."
)


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "core" / "x").mkdir(parents=True)
    (tmp_path / "core" / "x" / "loader.py").write_text("def load():\n    pass\n")
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    return tmp_path


def routes(comments):
    return {
        "repos/o/r/issues/7/comments": [comments],
        "repos/o/r/issues/7": [issue_raw(7)],
    }


def test_scorecard_checks_the_files_a_plan_names(capsys, checkout):
    comments = [
        comment_item("owner", "Keep it to the loader, please.", assoc="OWNER"),
        comment_item("alice", PLAN_A),
        comment_item("bob", "can I take this?"),
    ]
    assert main(["scorecard", "o/r", "7", "--checkout", str(checkout)], run=fake_gh(routes(comments))) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("2 claims →")
    assert "`core/x/loader.py` ✓" in out
    assert "`core/y/gone.py` ✗" in out
    assert "Keep it to the loader, please." in out


def test_scorecard_never_shows_real_logins(capsys, checkout):
    comments = [comment_item("alice", PLAN_A), comment_item("bob", "can I take this?"), comment_item("alice", "ping")]
    main(["scorecard", "o/r", "7", "--checkout", str(checkout)], run=fake_gh(routes(comments)))
    out = capsys.readouterr().out
    assert "alice" not in out and "bob" not in out
    assert "contributor-1" in out and "contributor-2" in out


def test_scorecard_full_lifts_the_row_cap(capsys, checkout):
    comments = [comment_item(f"user{i}", "can I take this?") for i in range(12)]
    run = fake_gh(routes(comments))
    main(["scorecard", "o/r", "7", "--checkout", str(checkout)], run=run)
    assert "…and 2 more" in capsys.readouterr().out
    main(["scorecard", "o/r", "7", "--checkout", str(checkout), "--full"], run=run)
    out = capsys.readouterr().out
    assert "…and" not in out
    assert "contributor-12" in out
