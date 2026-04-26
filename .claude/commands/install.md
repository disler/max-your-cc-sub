---
description: Install max-your-cc-sub — prerequisites, credentials, and one-shot verification
---

# Install max-your-cc-sub

## Purpose

Set up the max-your-cc-sub companion repo. This project has **no build step
and no dependency install** — every example is a PEP 723 single-file Python
script (`uv run` resolves dependencies on first run). Install is essentially:
verify three CLI tools, help the user set up at least one credential, and
confirm the `just` recipes are discoverable. Tested on macOS and Linux;
Windows works via WSL or Git Bash (the `just` recipes use POSIX shell
syntax).

This is an interactive, agentic process — ask the user when choices are
needed (especially around which credential path to set up first).

## Variables

SOURCE_REPO: The directory this command is running from
ENV_TEMPLATE: `.env.example`
ENV_FILE: `.env`
JUSTFILE: `justfile`

## Codebase Structure

```
max-your-cc-sub/
├── README.md                # repo overview + quickstart
├── LICENSE                  # MIT
├── justfile                 # one-shot recipes (check, oauth-*, api-*, compare)
├── .env.example             # copy to .env and fill in credentials
├── examples/
│   ├── 01_oauth_cli.py      # OAuth via Claude Code CLI
│   ├── 02_oauth_sdk.py      # OAuth via Claude Agent SDK
│   ├── 03_api_key_cli.py    # API key via Claude Code CLI
│   ├── 04_api_key_sdk.py    # API key via Claude Agent SDK
│   └── _compare_signals.py  # helper for `just compare`
└── logs/                    # per-recipe outputs, overwritten each run
    ├── check/status.txt
    ├── oauth-cli/events.ndjson
    ├── oauth-sdk/events.ndjson
    ├── api-cli/events.ndjson
    ├── api-sdk/events.ndjson
    └── compare/summary.txt
```

## Instructions

- Run every check via Bash — do not assume anything is installed.
- Show a status line immediately after each check (`OK` or `MISSING`).
- `claude`, `just`, and `uv` are all **critical** — stop and guide the user if any is missing. All four example scripts are invoked via `uv run`.
- Do NOT read or display the value of `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` — only confirm they are set and show the first 14 characters for prefix verification.
- Do NOT run `claude setup-token` from this command — it requires an interactive terminal with a browser. Tell the user to run it themselves in a fresh terminal.
- At least one credential must be configured before this command reports ready. If neither is set, help the user choose which to configure.

## Workflow

### Step 1 — Check Prerequisites

Run all three in parallel via Bash. Report pass/fail for each.

1. **`claude`** (critical — the Claude Code CLI)
   - Check: `command -v claude`
   - Version: `claude --version`
   - Install: `curl -fsSL https://claude.ai/install.sh | bash` (or see https://code.claude.com/)
   - Gate: stop if missing. Every example spawns `claude -p` or the SDK which wraps it.

2. **`just`** (critical — the task runner)
   - Check: `command -v just`
   - Version: `just --version`
   - Install: `brew install just` (macOS) / `winget install Casey.Just` (Windows) / package manager on Linux
   - Docs: https://github.com/casey/just
   - Gate: stop if missing. Every documented workflow uses `just <recipe>`.

3. **`uv`** (critical — runs every example as a PEP 723 single-file Python script)
   - Check: `command -v uv`
   - Version: `uv --version`
   - Install: `brew install uv` (macOS) / `winget install astral-sh.uv` (Windows) / `curl -LsSf https://astral.sh/uv/install.sh | sh` (anywhere)
   - Docs: https://docs.astral.sh/uv/
   - Gate: stop if missing. All four examples and the compare helper are invoked via `uv run`.

### Step 2 — Set Up Environment File

1. Check whether `.env` exists in the repo root.
2. If not, copy the template: `cp .env.example .env`.
3. Report the path to `.env` and that the user will fill credentials next.
4. Never read `.env` contents for display — only confirm the file exists.

### Step 3 — Configure At Least One Credential

Ask the user which path to set up first (single-select):

- **OAuth subscription token** — for personal/individual use, billed against their Claude Pro/Max subscription.
- **API key** — for any product, service, internal tool, or anything others use.
- **Both** — set up both, the examples can run either path.

For each selected path:

**OAuth token:**

1. Check `CLAUDE_CODE_OAUTH_TOKEN` env var in the current session. If set and starts with `sk-ant-oat01-`, mark OK (show only the first 14 characters).
2. If not set or wrong prefix, instruct the user:
   - "Open a new terminal (must have a browser), run: `claude setup-token`"
   - "Docs for what this flow does: https://code.claude.com/docs/en/authentication#generate-a-long-lived-token"
   - "Copy the printed `sk-ant-oat01-…` token"
   - "Paste it into `.env` on the `CLAUDE_CODE_OAUTH_TOKEN=` line"
3. Do NOT run `claude setup-token` from this command — it requires raw-mode TTY.
4. After the user confirms, re-check (they may need to `source .env` or start a new shell).

**API key:**

1. Check `ANTHROPIC_API_KEY` env var. If set and starts with `sk-ant-api`, mark OK (show only the first 14 characters).
2. If not set or wrong prefix, instruct the user:
   - "Create an API key at https://console.anthropic.com/ → Settings → API Keys"
   - "Paste it into `.env` on the `ANTHROPIC_API_KEY=` line"
3. After the user confirms, re-check.

### Step 4 — Verify Readiness

Never start anything. Just confirm the pieces line up.

1. **`justfile` is discoverable** — run `just --list` from the repo root and confirm it prints recipes without error.
2. **Example scripts are present** — confirm all four exist: `examples/01_oauth_cli.py`, `examples/02_oauth_sdk.py`, `examples/03_api_key_cli.py`, `examples/04_api_key_sdk.py`. No executable bit needed; `uv run` handles everything.
3. **Logs directory writable** — confirm `logs/` is writable. Scripts create per-recipe subdirs (`logs/oauth-cli/`, `logs/api-cli/`, etc.) on demand and overwrite the files on each run — no cleanup step needed.

### Step 5 — Report

Print a status table:

| Check | Status |
|---|---|
| claude CLI | OK / MISSING |
| just | OK / MISSING |
| uv | OK / MISSING |
| .env file | OK / CREATED |
| OAuth token | OK (`sk-ant-oat01-…`) / NOT SET |
| API key | OK (`sk-ant-api03-…`) / NOT SET |
| justfile recipes | OK (N recipes) |

Then a ready count (e.g. `7/8 checks passed`) and next steps:

- If OAuth set: `just oauth-cli` then `just oauth-sdk` (or `just oauth` for both)
- If API key set: `just api-cli` then `just api-sdk` (or `just api` for both)
- If both set: `just compare` to run one of each and see the auth signals side-by-side
- Always: `just check` any time to re-run prerequisite + credential verification
- Further reading: `README.md` (rules, signals table, references)

If any critical check failed, stop before the next-steps section and tell the user exactly which prerequisite to install.
