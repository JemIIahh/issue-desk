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

Gate-check fallback: not needed
