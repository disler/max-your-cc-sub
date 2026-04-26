---
description: Prime context for max-your-cc-sub — the OAuth-vs-API-key Claude Code walkthrough
---

# Purpose

Get oriented in `max-your-cc-sub`: a tiny PEP 723 / `uv` + `just` repo whose four
example scripts demonstrate running Claude Code under a Pro/Max subscription
OAuth token vs. a Console API key, and document where that line is bannable.

## Workflow

1. Run `git ls-files` to see the full tracked layout (it's small — read all of it).
2. Read `README.md` for the project's framing, the "one rule," the three usage
   tiers (green/gray/red), and the auth-signal table.
3. Read `justfile` to learn the recipe surface (`check`, `oauth`, `api`, `compare`,
   `oauth-setup`) and how `.env` flows through.
4. Glob `examples/*.py` and skim the four numbered examples plus
   `_compare_signals.py` — note which auth path each one exercises and what
   stream-json fields it extracts.
5. Skim `.env.example` and `.claude/commands/install.md` to understand the
   required credentials and the interactive setup flow.
6. Summarize your understanding of the project: purpose, stack, structure,
   key files, and entry points.
