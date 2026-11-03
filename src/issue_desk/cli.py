"""The issue-desk command line. It wraps triage-kit; subcommands are filled in task by task."""

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

from triage_kit.claims import anonymise, build_scorecard, render_scorecard
from triage_kit.gh import GhError, GitError, Runner, fetch_issue, list_open_issue_summaries, list_open_prs, run_gh
from triage_kit.mirror import mirror_issue
from triage_kit.sweep import hot_issues, render_sweep

UNBUILT = ("bench", "seed-practice", "doctor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="issue-desk", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sweep = sub.add_parser("sweep", help="list the issues drawing the most claims and competing PRs")
    sweep.add_argument("repo", help="owner/name")
    sweep.add_argument("--label", help="only issues with this label")

    card = sub.add_parser("scorecard", help="score the claim comments on one issue, with evidence")
    card.add_argument("repo", help="owner/name")
    card.add_argument("issue", type=int)
    card.add_argument("--checkout", required=True, help="a local clone of the repo, to check the files plans name")
    card.add_argument("--full", action="store_true", help="show every row, not just the first 10")

    mirror = sub.add_parser("mirror", help="copy an issue, usernames replaced, into your own PRIVATE sandbox repo")
    mirror.add_argument("source", help="owner/name of the issue to copy")
    mirror.add_argument("issue", type=int)
    mirror.add_argument("--to", required=True, help="owner/name of your private sandbox repo")

    for name in UNBUILT:
        stub = sub.add_parser(name)
        stub.add_argument("args", nargs=argparse.REMAINDER)
    return parser


Sleeper = Callable[[float], None]
POST_DELAY = 1.0  # seconds between writes, so a long thread does not trip GitHub's rate limits


def cmd_sweep(args: argparse.Namespace, run: Runner, sleep: Sleeper) -> str:
    issues = list_open_issue_summaries(args.repo, args.label, run)
    return render_sweep(hot_issues(issues, list_open_prs(args.repo, run)), args.repo)


def cmd_scorecard(args: argparse.Namespace, run: Runner, sleep: Sleeper) -> str:
    # Authors are replaced before anything is built, so no real login can reach the output.
    issue = anonymise(fetch_issue(args.repo, args.issue, run))
    rows, notes = build_scorecard(issue, Path(args.checkout))
    return render_scorecard(rows, notes, None if args.full else 10)


def paced(run: Runner, sleep: Sleeper, delay: float = POST_DELAY) -> Runner:
    """A runner that waits after every POST."""

    def wrapper(args: list[str]) -> str:
        out = run(args)
        if "POST" in args:
            sleep(delay)
        return out

    return wrapper


def cmd_mirror(args: argparse.Namespace, run: Runner, sleep: Sleeper) -> str:
    new = mirror_issue(args.source, args.issue, args.to, paced(run, sleep))
    return f"Mirrored {args.source}#{args.issue} → {args.to}#{new}"


COMMANDS = {"sweep": cmd_sweep, "scorecard": cmd_scorecard, "mirror": cmd_mirror}


def main(argv: list[str] | None = None, *, run: Runner = run_gh, sleep: Sleeper = time.sleep) -> int:
    args = build_parser().parse_args(argv)
    handler = COMMANDS.get(args.command)
    if handler is None:
        print(f"issue-desk {args.command}: not built yet", file=sys.stderr)
        return 2
    try:
        print(handler(args, run, sleep))
    except (GhError, GitError, ValueError) as err:
        print(f"issue-desk {args.command}: {err}", file=sys.stderr)
        return 1
    return 0
