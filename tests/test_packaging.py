import re
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_triage_kit_is_pinned_to_a_commit_in_the_standard_dependency_list():
    # A bare "triage-kit" would be looked up on PyPI by any installer that ignores [tool.uv.sources].
    deps = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    pinned = [d for d in deps if re.fullmatch(r"triage-kit @ git\+https://github\.com/JemIIahh/triage-kit@[0-9a-f]{40}", d)]
    assert pinned, deps
    assert "triage-kit" not in deps
