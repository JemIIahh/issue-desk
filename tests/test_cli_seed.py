import itertools
import json
import re
from pathlib import Path

from issue_desk.cli import DEFAULT_PRACTICE_DIR, main

NAMES = ["good", "failing", "sprawling", "sneaky"]


def fakes(private=True):
    gh_calls, git_calls = [], []
    numbers = itertools.count(11)

    def gh(args):
        gh_calls.append(list(args))
        if args[0] == "api":
            return json.dumps({"private": private, "default_branch": "main"})
        if args[:2] == ["pr", "create"]:
            return f"https://github.com/o/sb/pull/{next(numbers)}\n"
        raise AssertionError(f"unexpected gh call: {args}")

    def git(args):
        git_calls.append(list(args))
        return "Practice subject\n" if "log" in args else ""

    return gh, git, gh_calls, git_calls


def seed(tmp_path, gh, git):
    return main(["seed-practice", str(tmp_path), "o/sb", "5"], run=gh, git=git)


def test_seed_practice_opens_one_closing_pr_per_bundled_patch(capsys, tmp_path):
    gh, git, gh_calls, _ = fakes()
    assert seed(tmp_path, gh, git) == 0
    creates = [c for c in gh_calls if c[:2] == ["pr", "create"]]
    assert [c[c.index("--head") + 1] for c in creates] == [f"practice/{n}" for n in NAMES]
    assert all("Closes #5" in c[c.index("--body") + 1] for c in creates)
    assert all(c[c.index("--repo") + 1] == "o/sb" for c in creates)
    assert "#11, #12, #13, #14" in capsys.readouterr().out


def test_seed_practice_pushes_to_the_sandbox_by_url_never_to_origin(tmp_path):
    gh, git, _, git_calls = fakes()
    seed(tmp_path, gh, git)
    pushes = [c for c in git_calls if "push" in c]
    assert len(pushes) == len(NAMES)
    assert all("https://github.com/o/sb.git" in c and "origin" not in c for c in pushes)


def test_seed_practice_refuses_a_repo_that_is_not_private_and_touches_nothing(capsys, tmp_path):
    gh, git, gh_calls, git_calls = fakes(private=False)
    assert seed(tmp_path, gh, git) == 1
    assert "not private" in capsys.readouterr().err
    assert git_calls == []
    assert not [c for c in gh_calls if c[:2] == ["pr", "create"]]


def test_the_bundled_practice_patches_are_complete_and_say_where_they_came_from():
    assert re.fullmatch(r"[0-9a-f]{40}", (DEFAULT_PRACTICE_DIR / "BASE").read_text().strip())
    for name in NAMES:
        assert (DEFAULT_PRACTICE_DIR / f"{name}.patch").read_text().startswith("From ")
    note = (DEFAULT_PRACTICE_DIR / "README.md").read_text()
    assert "triage-kit" in note and "before the hackathon" in note
