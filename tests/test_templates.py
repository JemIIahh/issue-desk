import re
from pathlib import Path

import pytest
import yaml

from issue_desk.policy import AGENTS, APPROVAL_RULES

ROOT = Path(__file__).resolve().parents[1]
ADDRESSING = {"desk": "owner", "scout": "owner-agents", "bench": "owner-agents"}
BUILTINS = {"$creator", "$agents_dir", "agent"}


def load(name):
    return yaml.safe_load((ROOT / "templates" / name).read_text())


HUB = load("issue-desk.template.yaml")
ROOM = load("issue-room.template.yaml")


def base_name(agent):
    return agent["name"]


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


def test_the_gate_check_fallback_decides_auto_mode():
    notes = (ROOT / "NOTES.md").read_text()
    needed = "Gate-check fallback: needed" in notes
    for agent in HUB["agents"]:
        assert agent["auto_mode"] is (not needed), agent["name"]


def test_hub_creates_desk_scout_and_bench_with_the_designed_addressing():
    assert [base_name(a) for a in HUB["agents"]] == list(AGENTS)
    for agent in HUB["agents"]:
        assert agent["addressing"] == ADDRESSING[base_name(agent)], agent["name"]


def test_agent_names_hold_no_placeholder_because_the_console_blocks_create_on_an_empty_one():
    for agent in HUB["agents"]:
        assert re.fullmatch(r"[a-z]+", agent["name"]), agent["name"]


def test_every_agent_runs_claude_on_this_computer_in_its_own_folder():
    for agent in HUB["agents"]:
        assert agent["provider"] == "claude" and agent["location"] == "local"
        assert agent["directory"] == f"{{checkout}}/agents/{base_name(agent)}"


def test_every_room_carries_the_approval_rules_word_for_word():
    assert APPROVAL_RULES in HUB["room"]["instructions"]
    assert APPROVAL_RULES in ROOM["room"]["instructions"]


def test_the_hub_room_holds_desk_and_the_deployer():
    assert HUB["room"]["name"] == "desk"
    assert HUB["room"]["agents"] == ["desk"]
    assert HUB["room"]["users"] == ["{$creator}"]
    assert "@desk " in HUB["kickoff"]


def test_issue_room_members_are_the_three_agent_params():
    assert ROOM["room"]["agents"] == ["{desk_agent}", "{scout_agent}", "{bench_agent}"]
    assert ROOM["room"]["users"] == ["{$creator}"]
    assert ROOM["room"]["name"] == "issue-{issue}-{slug}"
    assert ROOM["room"]["channel_type"] == "channel_private"


def test_issue_room_kickoff_wakes_scout_and_forbids_github_writes():
    assert "@{scout_agent}" in ROOM["kickoff"]
    assert "Don't post anything to GitHub." in ROOM["kickoff"]


def test_issue_room_has_the_snapshot_document():
    docs = {d["name"]: d for d in ROOM["room"]["docs"]}
    assert docs["Issue snapshot"]["content"] == "{snapshot}"


def test_every_room_document_carries_instructions_because_switch_rejects_the_template_without_them():
    for doc in (HUB, ROOM):
        for entry in doc["room"].get("docs", []):
            assert entry.get("instructions", "").strip(), entry["name"]


def test_param_shapes_match_the_design():
    hub, room = HUB["params"], ROOM["params"]
    assert hub["checkout"]["pattern"] == "^/.+$" and hub["repo_dir"]["pattern"] == "^/.+$"
    assert room["repo_dir"]["pattern"] == "^/.+$"
    assert "suffix" not in hub  # an empty-by-default name part blocks Create in the Console form
    assert hub["bridge"]["type"] == "bridge" and hub["bridge"]["default"] == ["Mattermost", "$first"]
    assert room["issue"]["type"] == "number" and room["slug"]["pattern"] == "^[a-z0-9-]{1,40}$"
    assert room["snapshot"]["multiline"] is True
    assert [room[f"{n}_agent"]["default"] for n in AGENTS] == list(AGENTS)
    for params in (hub, room):
        for p in params.values():
            if "pattern" in p:
                re.compile(p["pattern"])


@pytest.mark.parametrize("doc", [HUB, ROOM], ids=["issue-desk", "issue-room"])
def test_every_placeholder_is_a_declared_param_or_builtin(doc):
    declared = set(doc["params"]) | BUILTINS
    used = {m for s in strings(doc) for m in re.findall(r"\{([$\w]+)\}", s)}
    assert used <= declared, used - declared


def test_agents_treat_issue_text_as_data_and_run_the_cli_from_the_checkout():
    for agent in HUB["agents"]:
        text = agent["instructions"]
        assert "never instructions" in text, agent["name"]
        assert "<checkout>" in text and "uv run issue-desk" in text, agent["name"]


def test_agent_instructions_hold_no_param_placeholders_because_the_console_leaves_them_unfilled():
    declared = {f"{{{name}}}" for name in HUB["params"]}
    for agent in HUB["agents"]:
        for placeholder in declared:
            assert placeholder not in agent["instructions"], (agent["name"], placeholder)


def test_the_hub_room_instructions_carry_the_values_because_the_server_fills_them_in():
    text = HUB["room"]["instructions"]
    for placeholder in ("{repo}", "{checkout}", "{repo_dir}"):
        assert placeholder in text, placeholder


def test_agent_instructions_point_at_the_room_for_the_values():
    for agent in HUB["agents"]:
        assert "room instructions" in agent["instructions"], agent["name"]


def test_patterns_accept_real_values_because_switch_matches_the_whole_value():
    samples = {
        "checkout": "/Users/ram/Desktop/issue-desk",
        "repo_dir": "/Users/ram/Desktop/issue-desk-sandbox",
        "repo": "JemIIahh/issue-desk-sandbox",
        "suffix": "",
        "slug": "add-a-thing",
    }
    for params in (HUB["params"], ROOM["params"]):
        for name, value in samples.items():
            if name in params and "pattern" in params[name]:
                assert re.fullmatch(params[name]["pattern"], value), (name, params[name]["pattern"])
