"""The issue-desk command line. Subcommands are filled in task by task."""

import argparse
import sys

COMMANDS = ("sweep", "scorecard", "mirror", "bench", "seed-practice", "doctor")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="issue-desk", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        stub = sub.add_parser(name)
        stub.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"issue-desk {args.command}: not built yet", file=sys.stderr)
    return 2
