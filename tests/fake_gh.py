"""A fake `gh` runner: answers `gh api ...` calls from a table of path prefixes."""

import json


def fake_gh(routes: dict):
    """routes maps a path prefix to the JSON payload `gh api --paginate --slurp` would print.

    The returned runner records every call in `.calls`.
    """

    def run(args: list[str]) -> str:
        run.calls.append(list(args))
        path = args[-1] if "-f" not in args else next(a for a in args if a.startswith("repos/"))
        for prefix, payload in routes.items():
            if path.startswith(prefix):
                return json.dumps(payload() if callable(payload) else payload)
        raise AssertionError(f"unexpected gh call: {args}")

    run.calls = []
    return run


def issue_item(number, title, comments=0, labels=(), assignees=()):
    return {
        "number": number,
        "title": title,
        "comments": comments,
        "labels": [{"name": n} for n in labels],
        "assignees": [{"login": n} for n in assignees],
    }


def pr_item(number, title, body, login="someone", ref="branch"):
    return {
        "number": number,
        "title": title,
        "body": body,
        "user": {"login": login},
        "head": {"ref": ref},
        "html_url": f"https://github.com/o/r/pull/{number}",
    }


def issue_raw(number, title="An issue", body="", login="owner", assoc="OWNER"):
    """The single-issue payload; `gh api --paginate --slurp` wraps it in a one-element list."""
    return {"number": number, "title": title, "body": body, "user": {"login": login}, "author_association": assoc, "labels": []}


def comment_item(login, body, assoc="NONE"):
    return {"user": {"login": login}, "author_association": assoc, "body": body, "created_at": "2026-01-01T00:00:00Z"}
