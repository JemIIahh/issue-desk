# Notes

## Task 2: Switch gate check (2026-11-03, Console 0.40.1, switch-core 0.31.0)

- **Project rules are honoured.** A Claude agent whose folder holds our `.claude/settings.json` raised an approval card for `gh issue comment --help` (ask rule), ran `gh --version` with no card (control), and refused `git -C . push --help` (deny rule, no card). So the `auto_mode: false` fallback is NOT needed.
- **The card** is posted in the thread of the request that started the work: "Permission needed · request A1 … Reply with `A1` and your choice, e.g. `A1 1`", with the options 1 Allow once / 2 Allow for this session / 3 Decline. In rehearsal the owner answers with the typed reply. Whether Mattermost draws buttons was not checked. An unanswered card ends the agent's turn with the tool call failed (about 2m48s here).
- **Switch tools:** `run_template` and `link_rooms` are in the agent's tool list (59 Switch tools; also `create_room_from_yaml`, `create_agent`, `post_message`, `list_templates`). Listed only, not exercised yet. Task 7 acceptance exercises them.
- **Setup gotchas for the README "Try it":**
  - The bundled Mattermost runs in Docker beside the server, so start Docker first.
  - If Docker was down when the Console started, rooms fail with "Bridge not running". Fix: start the Mattermost container, then Admin → Status → Restart.
  - The Console's agent form has no typeable directory (picker only). Templates set `directory`, so agents get their folder from the template.
  - The agent form needs a Description before "Add agent" enables.

## Task 7: templates and the live acceptance (2026-11-03 evening, Console 0.40.1)

Acceptance ran in Mattermost against the private sandbox (`JemIIahh/issue-desk-sandbox`), twice (the second time after the fixes below):

- `@desk sweep` returned the table with sandbox issue #1 (55 comments, PRs #7 to #10).
- `@desk open 1` ran `run_template` and `link_rooms`: the room `issue-1-backup-restore-run-history` opened with desk, scout and bench in it, and desk linked it from the hub.
- scout posted the short scorecard, saved the full one as the room document `Scorecard`, named the two strongest plans with the file checks (names shown as `contributor-N`), and drafted the direction comment. Nothing reached GitHub on its own.
- `@scout post it` raised an approval card (`A1`). The sandbox issue kept its comment count until the card was approved; approving with `A1 1` posted the comment (55 to 56). Declining with `A1 3` posted nothing.

Gotchas found (for the README "Try it"):

- **Switch fills `{param}` in names, directories, room fields and documents, but NOT in an agent's `instructions`.** The agents therefore get no repo values in their own brief. Their instructions say `<repo>`, `<checkout>`, `<repo_dir>` and point at the "Setup" line of the room instructions, which the server does fill in. (First run: desk said "my setup still has the `{repo}` placeholder unfilled".)
- A room document needs an `instructions` field, or `run_template` rejects the whole template ("Issue snapshot has no instructions field"). desk reported it instead of working around it.
- The Console matches a string `pattern` against the WHOLE value, and a placeholder inside an agent name must not be empty. The templates avoid both.
- The approval reply (`A1 1`) is also delivered to the agent as a chat message, so the agent may answer "I don't understand A1 1". Harmless: the card itself is processed.
- Recreating the hub after deleting its room gives the Mattermost channel a suffix (`desk-e8f5cea5`), because the old channel is archived. The Switch room is still called `desk`.
- Templates screen in 0.40.1 has no "Runs" tab; check Your Rooms instead.
- Timings: `open 1` about 35 to 60 s, scout's triage about 2 minutes.

## Tasks 8 and 9: bench and the practice PRs, live (2026-11-03 night)

Acceptance in the issue room on the sandbox: `@bench compare` tested all four practice PRs in the sealed box and posted the table. #7 passed with nothing flagged (recommended); #8 failed its tests; #9 passed but listed `.github/workflows/ci.yml`, `.prettierrc`, `README.md` +1 more as out of scope and `dependencies changed`; #10 (the sneaky one) passed its tests but was flagged `network call added, reads credentials, blocked network attempt`. `@bench go with 7` drafted three short, polite notes (shown in the room first, based only on the box's output). `@bench post it` raised three approval cards in turn (A1, A2, A3 — the next card appears after the previous one is answered); after approval each note appeared on its sandbox PR.

Gotchas found:

- **bench cannot know a PR's own new test file from the README or CI**, and plain `npm test` would pass the buggy PR. So scout saves its draft as a room document `Direction` ending with `Scope:` / `Install:` / `Tests:` lines (the maintainer can change them in chat); bench reads them and asks only when one is missing. The three lines are for bench and stay off GitHub.
- A clone made with `git init` + `git remote add` has no `origin/HEAD`; the CLI now takes the base from the repo's default branch on GitHub.
- **Speed:** the box installs dependencies per PR, then saves that layer; about 3 minutes per PR, 14 minutes for four. bench posts "still running" meanwhile and its status line keeps showing the first seconds. An install cache keyed on the lockfile would cut it (not built).
- In the sandbox every practice PR is by the owner, so the Author column reads `maintainer` for all four.
- scout, asked to draft the Direction, cited where each of the three lines came from and asked what to keep off GitHub: good behaviour to keep.

Gate-check fallback: not needed

## Task 10: dress rehearsal 1 (2026-11-03 night)

Played the maintainer through issue #11 on the sandbox: sweep, open, scout's triage, the Scope/Install/Tests edit, `post it` (card), `@bench compare`, `go with 12`, `post it` (three cards), `@desk digest`.

What the rehearsal found:

- **scout's first comment named files outside the Scope** the maintainer had just set. Fixed in the scout instruction (the body must stay inside `Scope:`; rewrite it if not).
- **desk's doctor line was vague.** desk now reports the real `doctor` output and explains each ✗ line.
- **Asking `@bench compare` a second time does nothing new:** Switch tells the agent "this request already ran" and bench replies with the earlier summary and offers "re-run". Harmless; a recording is made on a fresh room so it does not come up.
- **Approval card numbers run on through a room.** scout's comment is `A1`, bench's three notes are `A2` to `A4`. Anything that answers cards must take the next unanswered one, not a fixed `A1`.
- **bench's drafts were accurate and polite** (#13 failed its tests, #14 edited CI config and dependencies, #15 added a network call and read credentials); #12, the pick, got no note. Each note posted only after its own card.
- **desk's digest** listed what came in (55 claims: 42 bare, 12 plans), what was decided and what is waiting.
- Speed: bench about 11 minutes for four PRs on a warm machine, scout about 3 minutes.
