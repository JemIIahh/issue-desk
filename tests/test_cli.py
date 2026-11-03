import argparse

from issue_desk.cli import COMMANDS, build_parser


def test_every_subcommand_has_a_handler_and_every_handler_a_subcommand():
    sub = next(a for a in build_parser()._actions if isinstance(a, argparse._SubParsersAction))
    assert set(sub.choices) == set(COMMANDS)
