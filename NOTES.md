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
