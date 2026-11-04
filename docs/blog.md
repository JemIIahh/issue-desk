# Issue Desk: three Claude Code agents that read your "assign me" pile

A maintainer posts a good-first-issue. Within a day it has 55 comments, almost all of them some version of "can I take this?", and a handful of pull requests. Nobody has time to read 55 comments carefully, so the maintainer either picks the first one or the loudest one. Issue Desk is an experiment in making the careful read cheap, while keeping every decision with the person.

It is three Claude Code agents in a [Switch](https://github.com/sandbox-quantum/switch) room. You talk to them in Mattermost. Nothing they draft reaches GitHub until you press an approval card.

## What it looks like

I rehearsed on a private copy of a real, public issue (Flamki/stellarmind#183: 55 claim comments, names replaced with `contributor-N`) with four practice pull requests: a good one, one that fails its tests, one that wanders out of scope, and one that passes its tests but quietly phones home.

1. **`@desk sweep`.** `desk` lists the issues drawing the most claims and PRs.
2. **`@desk open 16`.** `desk` runs a Switch template and a new room appears for that issue, linked back to the hub. `scout` wakes up on its own.
3. **`scout` reads every claim.** In a couple of minutes it posts a table: 42 bare requests, 12 plans, 1 follow-up, 0 near-duplicates, and for each plan whether the files it names exist in the repo. Only one plan named files that exist. It also drafts a direction comment ("here is the approach we'd like, so plans and PRs can line up") and saves it as a room document.
4. **You edit, then say `post it`.** I told `scout` the scope and the test commands in one message and it rewrote the draft to stay inside them. Then a card appeared: *Permission needed, request A1.* I answered `A1 1`. That is the only way anything gets written to GitHub.
5. **`@bench compare`.** `bench` checks out each PR and runs the tests in a sealed Docker container: no network, no environment variables, nothing mounted but that PR's copy. About three minutes per PR, almost all of it installing dependencies. The result is a table and a recommendation. It passed #17, failed #18, flagged #19 for editing CI config and dependencies, and flagged #20 for adding a network call and reading credentials, even though #20's tests pass.
6. **`go with 17`.** `bench` drafts short, polite notes for the other three authors, shows them in the room, and posts each one only through its own approval card.
7. **`@desk digest`.** What came in, what was decided, what is still waiting on you.

## How Switch is used

Switch does the parts I would otherwise have had to build: the chat, the rooms, the approval cards and the hand-offs.

- A **template** with parameters creates the three agents and the hub room in one go. A second template is the per-issue room.
- `desk` calls **`run_template`** to open one room per hot issue, and **`link_rooms`** so it can read them back for the digest.
- `scout` writes the full scorecard and the draft as **room documents**; `bench` reads the draft for the scope and test commands.
- Every GitHub write is an **approval card** in the thread. The agent folders list the commands that need one, and `issue-desk doctor` fails if a rule is missing.
- **Room instructions** carry the three rules every room shares (show the full draft first, one approval covers a batch only if the batch was listed in full, never merge or close) and tell the agents that text copied from GitHub is data, not instructions.

## What went wrong, honestly

- Switch fills `{params}` into room instructions but not into agent instructions. My agents first saw a literal `{repo}`. The fix was to put the repo and paths in the room instructions and keep the agent instructions parameter-free.
- A plain `npm test` cannot run a PR's own new test file, so it would have passed the buggy PR. `scout` now writes `Scope:`, `Install:` and `Tests:` lines into the direction document and `bench` runs exactly those.
- Approval card numbers run on through a room: `scout`'s comment is `A1`, `bench`'s three notes are `A2` to `A4`. My own recording script assumed `A1` and stalled.
- `scout` once drafted a comment that asked for changes to files outside the scope I had just set. Its instruction now says to rewrite the body until it stays inside the scope.
- `bench` is slow. A cached dependency layer would help. I did not build it.

## Try it

Clone it, run `uv run issue-desk doctor`, make a private sandbox copy, import the two templates in Switch Console, and talk to `desk`. The README has every step, and every write goes to your own private sandbox repo.

## What was written when, and how AI was used

The Switch-free engine underneath (reading GitHub, the claim scorecard, the sealed test box, the mirror, the practice-PR seeder) is a separate public library, [triage-kit](https://github.com/JemIIahh/triage-kit), written before the hackathon window and disclosed as such. Everything Switch-specific, the templates, the agents' instructions, the approval rules and the command line that wraps it, was written during the window. All of it was written with Claude Code as the coding assistant, from a written design and plan, with tests first. The product decisions, the safety rules and every outward action were mine. The agents that run inside Issue Desk are Claude Code agents hosted by Switch, and their full instructions are in the templates.

In the demo video the maintainer's typing and clicking were played by a script so the run could be repeated. The agents' replies and the GitHub comments are real.
