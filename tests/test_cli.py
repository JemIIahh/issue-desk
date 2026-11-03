import pytest

from issue_desk.cli import main

# Each later task builds one of these and removes its name from the list.
UNBUILT = ["sweep", "scorecard", "mirror", "bench", "seed-practice", "doctor"]


@pytest.mark.parametrize("command", UNBUILT)
def test_unbuilt_command_exits_2_and_says_so(command, capsys):
    assert main([command]) == 2
    assert "not built yet" in capsys.readouterr().err
