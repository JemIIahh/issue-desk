"""Permission rules every agent's Claude Code settings must carry, and the room rules."""

AGENTS = ("desk", "scout", "bench")

# Every GitHub write raises an approval card.
REQUIRED_ASK: tuple[str, ...] = (
    "Bash(gh issue comment:*)",
    "Bash(gh pr comment:*)",
    "Bash(gh pr review:*)",
    "Bash(gh issue edit:*)",
    "Bash(gh label:*)",
    "Bash(gh api:*)",
    "Bash(curl:*)",
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
