"""The issue-desk command line. It wraps triage-kit; subcommands are filled in task by task."""

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

from triage_kit.bench import (
    PrResult,
    diff_stats,
    out_of_scope,
    prepare_worktree,
    prs_for_issue,
    render_comparison,
    risk_flags,
    run_tests,
)
from triage_kit.claims import anonymise, build_scorecard, render_scorecard
from triage_kit.gh import GhError, GitError, Runner, fetch_issue, list_open_issue_summaries, list_open_prs, run_gh, run_git
from triage_kit.models import Issue, PullRequest
from triage_kit.mirror import mirror_issue
from triage_kit.sweep import hot_issues, render_sweep

UNBUILT = ("seed-practice", "doctor")
# Pull-request checkouts live here, outside every folder an agent works in, so a PR's own
# CLAUDE.md or .claude/ is never loaded by an agent.
DEFAULT_WORK_ROOT = Path.home() / ".cache" / "issue-desk" / "work"


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

    bench = sub.add_parser("bench", help="test and compare the open PRs that close an issue, each in a sealed box")
    bench.add_argument("repo", help="owner/name")
    bench.add_argument("issue", type=int)
    bench.add_argument("--repo-dir", required=True, help="a local clone of the repo")
    bench.add_argument("--scope", action="append", required=True, metavar="GLOB", help="a path the agreed direction allows; repeat for more")
    bench.add_argument("--test-cmd", required=True, help="the command that runs the repo's tests")
    bench.add_argument("--install-cmd", help="the command that installs dependencies (runs with network, scripts off)")
    bench.add_argument("--image", default="node:20-slim", help="the Docker image the tests run in")
    bench.add_argument("--base", default="origin/HEAD", help="what each PR is diffed against")
    bench.add_argument("--work-root", default=str(DEFAULT_WORK_ROOT), help=argparse.SUPPRESS)

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


def author_pseudonyms(issue: Issue, prs: list[PullRequest]) -> dict[str, str]:
    """Map each PR author's login to the name the scorecard gives them.

    People in the issue thread keep their scorecard name; PR authors who are not in the
    thread are numbered after them. No real login is ever a value.
    """
    anon = anonymise(issue)
    names = {
        real.lower(): fake
        for real, fake in zip([issue.author, *(c.author for c in issue.comments)], [anon.author, *(c.author for c in anon.comments)])
    }
    taken = len({fake for fake in names.values() if fake != "maintainer"})
    for pr in prs:
        if pr.author.lower() not in names:
            taken += 1
            names[pr.author.lower()] = f"contributor-{taken}"
    return names


def cmd_bench(args: argparse.Namespace, run: Runner, sleep: Sleeper) -> str:
    if args.base.startswith("-"):
        raise ValueError(f"--base {args.base!r} looks like an option, not a git ref")
    prs = sorted(prs_for_issue(args.repo, args.issue, run), key=lambda p: p.number)
    if not prs:
        return f"No open pull requests close #{args.issue}."
    names = author_pseudonyms(fetch_issue(args.repo, args.issue, run), prs)
    repo_dir, root = Path(args.repo_dir), Path(args.work_root)
    results = []
    for pr in prs:
        worktree = prepare_worktree(repo_dir, pr, root)
        files, added, deleted = diff_stats(worktree, args.base)
        diff_text = run_git(["-C", str(worktree), "diff", f"{args.base}...HEAD"])
        status, tail, runtime = run_tests(worktree, args.image, args.install_cmd, args.test_cmd)
        flags = risk_flags(files, diff_text) + runtime
        results.append(
            PrResult(pr.number, names[pr.author.lower()], len(files), added, deleted, out_of_scope(files, args.scope), status, tail, flags)
        )
    return render_comparison(results)


COMMANDS = {"sweep": cmd_sweep, "scorecard": cmd_scorecard, "mirror": cmd_mirror, "bench": cmd_bench}


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
