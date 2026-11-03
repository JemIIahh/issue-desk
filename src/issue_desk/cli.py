"""The issue-desk command line. It wraps triage-kit; subcommands are filled in task by task."""

import argparse
import sys

from triage_kit.gh import GhError, GitError, Runner, list_open_issue_summaries, list_open_prs, run_gh
from triage_kit.sweep import hot_issues, render_sweep

UNBUILT = ("scorecard", "mirror", "bench", "seed-practice", "doctor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="issue-desk", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sweep = sub.add_parser("sweep", help="list the issues drawing the most claims and competing PRs")
    sweep.add_argument("repo", help="owner/name")
    sweep.add_argument("--label", help="only issues with this label")

    for name in UNBUILT:
        stub = sub.add_parser(name)
        stub.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def cmd_sweep(args: argparse.Namespace, run: Runner) -> str:
    issues = list_open_issue_summaries(args.repo, args.label, run)
    return render_sweep(hot_issues(issues, list_open_prs(args.repo, run)), args.repo)


COMMANDS = {"sweep": cmd_sweep}


def main(argv: list[str] | None = None, *, run: Runner = run_gh) -> int:
    args = build_parser().parse_args(argv)
    handler = COMMANDS.get(args.command)
    if handler is None:
        print(f"issue-desk {args.command}: not built yet", file=sys.stderr)
        return 2
    try:
        print(handler(args, run))
    except (GhError, GitError, ValueError) as err:
        print(f"issue-desk {args.command}: {err}", file=sys.stderr)
        return 1
    return 0
