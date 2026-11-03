from fake_gh import fake_gh, issue_item, pr_item
from triage_kit.gh import GhError

from issue_desk.cli import main


def routes():
    return {
        "repos/o/r/issues": [[issue_item(5, "Add x", comments=6), issue_item(6, "Quiet", comments=1)]],
        "repos/o/r/pulls": [[pr_item(10, "Fix x", "Closes #5")]],
    }


def test_sweep_prints_the_hot_issue_table(capsys):
    assert main(["sweep", "o/r"], run=fake_gh(routes())) == 0
    out = capsys.readouterr().out
    assert "| # | Title | Comments | Open PRs |" in out
    assert "| #5 | Add x | 6 | 1 (#10) |" in out
    assert "Quiet" not in out


def test_sweep_passes_the_label_to_the_issue_read():
    run = fake_gh(routes())
    main(["sweep", "o/r", "--label", "hackathon"], run=run)
    assert any("labels=hackathon" in call[-1] for call in run.calls)


def test_sweep_reports_a_gh_failure_and_exits_1(capsys):
    def broken(args):
        raise GhError("boom")

    assert main(["sweep", "o/r"], run=broken) == 1
    assert "boom" in capsys.readouterr().err
