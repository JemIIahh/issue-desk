from fake_gh import comment_item, fake_gh, issue_raw

from issue_desk.cli import main


def routes(private=True):
    # Most specific prefix first: the fake answers with the first match.
    return {
        "repos/me/sandbox/issues/9/comments": {},
        "repos/me/sandbox/issues": {"number": 9},
        "repos/me/sandbox": {"private": private},
        "repos/src/repo/issues/5/comments": [
            [comment_item("alice", "I'll take it"), comment_item("bob", "me too"), comment_item("alice", "ping")]
        ],
        "repos/src/repo/issues/5": [issue_raw(5, title="Add a thing", body="Please add a thing.")],
    }


def posts(run):
    return [call for call in run.calls if "POST" in call]


def test_mirror_posts_the_issue_and_every_comment_one_second_apart(capsys):
    run, sleeps = fake_gh(routes()), []
    assert main(["mirror", "src/repo", "5", "--to", "me/sandbox"], run=run, sleep=sleeps.append) == 0
    assert len(posts(run)) == 4  # the issue, then 3 comments
    assert sleeps == [1.0] * 4
    assert "me/sandbox#9" in capsys.readouterr().out


def test_mirror_posts_no_real_logins():
    run = fake_gh(routes())
    main(["mirror", "src/repo", "5", "--to", "me/sandbox"], run=run, sleep=lambda s: None)
    sent = " ".join(" ".join(call) for call in posts(run))
    assert "alice" not in sent and "bob" not in sent
    assert "**contributor-1** wrote:" in sent


def test_mirror_refuses_a_public_destination(capsys):
    run, sleeps = fake_gh(routes(private=False)), []
    assert main(["mirror", "src/repo", "5", "--to", "me/sandbox"], run=run, sleep=sleeps.append) == 1
    assert "not private" in capsys.readouterr().err
    assert posts(run) == [] and sleeps == []


def test_mirror_leaves_out_comments_written_by_a_github_app():
    # Mirroring replaces every login, so a copied `drips-wave[bot]` notice would read as one more human plan.
    r = routes()
    r["repos/src/repo/issues/5/comments"] = [
        [
            comment_item("alice", "I'll take it"),
            comment_item("drips-wave[bot]", "Congratulations, @alice! Your application was accepted."),
            comment_item("bob", "me too"),
        ]
    ]
    run = fake_gh(r)
    main(["mirror", "src/repo", "5", "--to", "me/sandbox"], run=run, sleep=lambda s: None)
    sent = " ".join(" ".join(call) for call in posts(run))
    assert len(posts(run)) == 3  # the issue and two human comments
    assert "Congratulations" not in sent
    assert "**contributor-2** wrote:\n\nme too" in sent  # the bot did not take a number
