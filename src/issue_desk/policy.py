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
    "Bash(python:*)",
    "Bash(python3:*)",
    "Bash(node:*)",
    "Bash(bash:*)",
    "Bash(sh:*)",
    "Bash(zsh:*)",
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
