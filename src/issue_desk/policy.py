"""Permission rules every agent's Claude Code settings must carry, and the room rules."""

AGENTS = ("desk", "scout", "bench")

# Rooms run in auto mode: a command that matches no rule runs with no card. So the ask list names every
# GitHub write the agents could plausibly run (not just the ones they are told to use), and the interpreters
# that could wrap one, so a roundabout form raises a card too.
REQUIRED_ASK: tuple[str, ...] = (
    "Bash(gh issue comment:*)",
    "Bash(gh pr comment:*)",
    "Bash(gh pr review:*)",
    "Bash(gh issue edit:*)",
    "Bash(gh label:*)",
    "Bash(gh api:*)",
    "Bash(curl:*)",
    "Bash(gh pr edit:*)",
    "Bash(gh pr create:*)",
    "Bash(gh pr ready:*)",
    "Bash(gh pr reopen:*)",
    "Bash(gh issue create:*)",
    "Bash(gh issue reopen:*)",
    "Bash(gh issue lock:*)",
    "Bash(gh issue unlock:*)",
    "Bash(gh issue pin:*)",
    "Bash(gh issue unpin:*)",
    "Bash(gh issue transfer:*)",
    "Bash(gh issue develop:*)",
    "Bash(gh release:*)",
    "Bash(gh workflow:*)",
    "Bash(gh run:*)",
    "Bash(gh pr lock:*)",
    "Bash(gh pr unlock:*)",
    "Bash(gh pr revert:*)",
    "Bash(python:*)",
    "Bash(python3:*)",
    "Bash(node:*)",
    "Bash(bash:*)",
    "Bash(sh:*)",
    "Bash(zsh:*)",
    # Wrappers (`env gh pr merge 7` starts with "env") and the git commands that bring a PR's code onto the
    # host; only `issue-desk bench` should do that.
    "Bash(env:*)",
    "Bash(command:*)",
    "Bash(xargs:*)",
    "Bash(timeout:*)",
    "Bash(nohup:*)",
    "Bash(exec:*)",
    "Bash(sudo:*)",
    "Bash(git fetch:*)",
    "Bash(git checkout:*)",
    "Bash(git switch:*)",
    "Bash(git worktree:*)",
    "Bash(git apply:*)",
    "Bash(git am:*)",
    "Bash(git pull:*)",
)

# Never allowed, even with approval.
REQUIRED_DENY: tuple[str, ...] = (
    "Bash(gh pr merge:*)",
    "Bash(gh pr close:*)",
    "Bash(gh issue close:*)",
    "Bash(git push:*)",
    "Bash(gh auth token:*)",
    "Bash(uv run issue-desk mirror:*)",
    "Bash(uv run issue-desk seed-practice:*)",
    # Forms the prefix rules above would miss: git global flags before "push", and the
    # maintainer-only commands run without "uv run".
    "Bash(git -C:*)",
    "Bash(git -c:*)",
    "Bash(issue-desk mirror:*)",
    "Bash(issue-desk seed-practice:*)",
    "Bash(python -m issue_desk:*)",
    "Bash(uv run python -m issue_desk:*)",
    # Account, repo and alias commands the agents never need ("gh auth status --show-token" prints the
    # token; an alias can hide "pr merge" behind another name).
    "Bash(gh alias:*)",
    "Bash(gh extension:*)",
    "Bash(gh auth:*)",
    "Bash(gh config:*)",
    "Bash(gh repo:*)",
    "Bash(gh gist:*)",
    "Bash(gh secret:*)",
    "Bash(gh variable:*)",
    "Bash(gh issue delete:*)",
    # `gh pr -R owner/repo merge 7` is valid gh and does not start with "gh pr merge", so the flag-first
    # forms are denied; the agents put --repo after the subcommand.
    "Bash(gh pr -R:*)",
    "Bash(gh pr --repo:*)",
    "Bash(gh issue -R:*)",
    "Bash(gh issue --repo:*)",
    "Bash(gh release -R:*)",
    "Bash(gh release --repo:*)",
    "Bash(gh run -R:*)",
    "Bash(gh run --repo:*)",
    "Bash(gh workflow -R:*)",
    "Bash(gh workflow --repo:*)",
    "Bash(gh label -R:*)",
    "Bash(gh label --repo:*)",
    # Pushes to a contributor's branch, and puts a PR's code on the host (only `issue-desk bench` runs it).
    "Bash(gh pr update-branch:*)",
    "Bash(gh pr checkout:*)",
    "Bash(gh cache:*)",
    "Bash(gh project:*)",
    "Bash(gh ruleset:*)",
    "Bash(gh codespace:*)",
    "Bash(gh org:*)",
    "Bash(gh ssh-key:*)",
    "Bash(gh gpg-key:*)",
    # Git global flags that put something between "git" and the subcommand.
    "Bash(git --git-dir:*)",
    "Bash(git --work-tree:*)",
    "Bash(git --no-pager:*)",
    "Bash(git -P:*)",
    "Bash(git -p:*)",
    "Bash(git --paginate:*)",
    "Bash(git --bare:*)",
    "Bash(git --namespace:*)",
    "Bash(git --exec-path:*)",
    "Bash(git --config-env:*)",
    "Bash(git --super-prefix:*)",
    "Bash(git --no-replace-objects:*)",
    "Bash(git --no-lazy-fetch:*)",
    "Bash(git --no-optional-locks:*)",
    "Bash(git --no-advice:*)",
    "Bash(git --literal-pathspecs:*)",
    "Bash(git --glob-pathspecs:*)",
    "Bash(git --noglob-pathspecs:*)",
    "Bash(git --icase-pathspecs:*)",
    "Bash(git --attr-source:*)",
)

# Written into every room's instructions (spec: "Approval rules").
APPROVAL_RULES = (
    "1. Always show the full draft in the room before trying to post it. "
    '"Post it" from the maintainer is the request; the approval card is the gate.\n'
    "2. One approval can cover a batch only if the batch was listed in full "
    '(for example, "reply to these 6 bare claims with the standard note").\n'
    "3. Agents never merge, never close PRs and never push to contributors' branches."
)


def missing_rules(settings: dict) -> list[str]:
    """Required rules absent from a settings dict: ask rules first, then deny rules."""
    permissions = settings.get("permissions", {})
    ask = set(permissions.get("ask", []))
    deny = set(permissions.get("deny", []))
    return [r for r in REQUIRED_ASK if r not in ask] + [r for r in REQUIRED_DENY if r not in deny]
