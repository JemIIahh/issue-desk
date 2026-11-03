# Practice pull requests for rehearsals

Four patches for [Flamki/stellarmind#183](https://github.com/Flamki/stellarmind/issues/183)
(a verified backup and restore for run history), written to rehearse a pull request
comparison. None was ever sent to the real project.

**Provenance: written before the hackathon.** These files are copied byte for byte from
[`examples/stellarmind-183`](https://github.com/JemIIahh/triage-kit/tree/85f42c68987c909d226d42380d594dc727e8bb5a/examples/stellarmind-183)
in the public `triage-kit` library (commit `85f42c6`, first written 2026-10-29, before the
hackathon window opened). They are test data, not part of the Switch setup, and are not new work.

| Patch | What it is | What the comparison should show |
|---|---|---|
| `good.patch` | Backup, verify and restore with a checksum, a CLI, tests and docs | tests pass, nothing out of scope |
| `failing.patch` | The same idea, but verify skips the checksum | a test fails on the damaged-backup case |
| `sprawling.patch` | The good change plus README, `package.json`, `.prettierrc` and CI edits | tests pass, 4 files out of scope, `dependencies changed` |
| `sneaky.patch` | The good change plus a hidden "usage report" that gathers secret-looking environment variables and posts them | tests pass, but flags `network call added`, `reads credentials`, `blocked network attempt` |

`sneaky.patch` stands in for a malicious pull request. It is harmless: it posts to
`collect.example`, a name reserved so it never points at a real server. In the sealed box there
is no network and no environment to read in any case. Do not merge it anywhere.

`BASE` is the stellarmind commit the patches apply to. `issue-desk seed-practice` branches from it
inside your own PRIVATE sandbox copy of stellarmind and opens one pull request per patch.
