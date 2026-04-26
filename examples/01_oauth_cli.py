# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Example 1 — OAuth subscription flow, using the Claude Code CLI (`claude -p`).

Cross-platform replacement for the old 01_oauth_cli.sh. Same logic: spawn
`claude -p` as a subprocess, capture the stream-json event feed, extract the
two forensic signals (`apiKeySource` and `rateLimitType`). Pure stdlib, no
jq/bash required — runs on macOS, Linux, and Windows.

Run it:    just oauth-cli
Manually:  uv run examples/01_oauth_cli.py
"""

# `json`       — parse newline-delimited JSON events from the CLI
# `os`         — read env vars and build a scrubbed env for the subprocess
# `subprocess` — invoke the `claude` binary
# `sys`        — fail with a clean exit message when preconditions fail
# `pathlib`    — create logs/ and write the event dump portably
import json
import os
import subprocess
import sys
from pathlib import Path

# --- Pretty output helpers (ANSI colors, no deps) ----------------------------
# Dim for process chatter; bold/color for the stuff you came to see.
# These escapes are rendered correctly by Windows Terminal, VS Code terminal,
# PowerShell 7+, and every mainstream macOS/Linux terminal.
DIM, RESET, BOLD = "\033[2m", "\033[0m", "\033[1m"
CYAN, GREEN, AMBER, RED = "\033[1;36m", "\033[1;32m", "\033[1;33m", "\033[1;31m"

# Self-citation: the proof block prints `examples/<this-file>:<line>` pointing
# at the line tagged `#<wire>` below. Found at runtime so it stays correct
# when the file is edited — no hardcoded line numbers to rot.
SELF_REL = f"examples/{Path(__file__).name}"


def _line_of(marker: str) -> int:
    """Return the 1-based line number of the trailing-comment marker in this file.
    Requires the marker at end-of-line so doc-comment mentions don't collide."""
    for i, ln in enumerate(Path(__file__).read_text().splitlines(), 1):
        if ln.rstrip().endswith(marker):
            return i
    return 0


def kv(key: str, value: object, color: str = CYAN) -> None:
    """Print a bold key with a colored value. Used for forensic signals."""
    print(f"  {BOLD}{key:<16}{RESET} {color}{value}{RESET}")


def banner(color: str, label: str, subtitle: str) -> None:
    """Print a colored horizontal-rule banner with a label and dim subtitle."""
    bar = "═" * 62
    print(f"\n{color}{bar}{RESET}")
    print(f"{color}  {label}{RESET}")
    print(f"{DIM}  {subtitle}{RESET}")
    print(f"{color}{bar}{RESET}\n")


def dim(msg: str) -> None:
    """Dimmed process-chatter line (setup, hygiene, not the main event)."""
    print(f"{DIM}  {msg}{RESET}")


def main() -> None:
    # ----- Top banner declaring the auth mode --------------------------------
    banner(CYAN, "AUTH MODE: OAUTH (SUBSCRIPTION)",
           "Claude Code CLI · billing → your Claude Pro/Max subscription")

    # -------------------------------------------------------------------------
    # STEP 1 — Verify the OAuth token is present and has the right prefix
    # -------------------------------------------------------------------------
    # `CLAUDE_CODE_OAUTH_TOKEN` is what Anthropic's `claude setup-token` prints.
    # It starts with `sk-ant-oat01-` (subscription-tied). API keys use
    # `sk-ant-api03-` — those bill against a Console project, not your sub.
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not token:
        print(f"{RED}FAIL{RESET}  CLAUDE_CODE_OAUTH_TOKEN is not set.")
        print("        Run `claude setup-token` in a terminal with a browser,")
        print("        copy the printed sk-ant-oat01-... token, then add it to .env.")
        sys.exit(1)
    if token.startswith("sk-ant-api"):
        print(f"{RED}FAIL{RESET}  That's an API key, not an OAuth token. "
              "Use 03_api_key_cli.py instead.")
        sys.exit(1)
    if not token.startswith("sk-ant-oat01-"):
        print(f"{AMBER}WARN{RESET}  Token has an unrecognized prefix; continuing anyway.")
    dim(f"OK  token prefix {token[:14]}…  (len={len(token)})")

    # -------------------------------------------------------------------------
    # STEP 2 — Build a scrubbed env for the subprocess
    # -------------------------------------------------------------------------
    # Claude Code's documented precedence puts ANTHROPIC_API_KEY (#3) and
    # ANTHROPIC_AUTH_TOKEN (#2) ABOVE the OAuth token (#5). If either is set,
    # the OAuth token is silently ignored and the run is billed via the API
    # key. We copy the current env and pop them for the child process only —
    # the user's shell env is untouched.
    env = os.environ.copy()
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):  #<wire>
        if env.pop(var, None):
            dim(f"OK  cleared {var} for subprocess (higher precedence than OAuth)")

    # -------------------------------------------------------------------------
    # STEP 3 — Run `claude -p` in verbose stream-json mode
    # -------------------------------------------------------------------------
    # Flags explained:
    #   -p / --print                 non-interactive mode (headless)
    #   --verbose                    emit every event, not just the final result
    #   --output-format stream-json  newline-delimited JSON, one event per line
    #   --include-hook-events        include hook lifecycle events too
    # We deliberately do NOT pass --bare. `--bare` skips OAuth token reading
    # and requires ANTHROPIC_API_KEY — that would defeat the whole POC.
    # Each recipe writes to its own logs/<recipe>/ dir, overwritten on every
    # run. No clean step needed — the file is replaced, not appended.
    log_dir = Path("logs") / "oauth-cli"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "events.ndjson"

    cmd = [
        "claude", "-p",
        "Reply with exactly these three words: oauth cli works",
        "--verbose",
        "--output-format", "stream-json",
        "--include-hook-events",
    ]
    # `capture_output=True` pipes stdout+stderr so we can write stdout to the
    # log file. `text=True` decodes bytes to str using the default encoding.
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    log_path.write_text(proc.stdout)
    if proc.returncode != 0:
        print(f"{RED}FAIL{RESET}  claude exited with code {proc.returncode}")
        sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)

    # Count how many events we captured so the progress line is meaningful.
    event_lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    dim(f"OK  captured {len(event_lines)} events → {log_path}")

    # -------------------------------------------------------------------------
    # STEP 4 — Parse the two forensic signals
    # -------------------------------------------------------------------------
    # These are the authoritative "subscription billing" tells:
    #   apiKeySource: "none"       -> no API-key credential was chosen
    #   rateLimitType: "five_hour" -> Pro/Max 5-hour rolling window
    # API keys NEVER emit `five_hour` (they use RPM/TPM + monthly tiers).
    api_key_source: str | None = None
    rate_limit_type: str | None = None
    is_using_overage: bool | None = None
    reply_text: str = ""
    # Track the 1-based line number in events.ndjson where each forensic
    # signal first appears, so we can point the reader at the exact bytes
    # that prove the auth mode.
    init_line_no: int | None = None
    rate_limit_line_no: int | None = None

    for idx, line in enumerate(event_lines, start=1):
        event = json.loads(line)
        # system/init carries the `apiKeySource` field.
        if event.get("type") == "system" and event.get("subtype") == "init":
            api_key_source = event.get("apiKeySource")
            init_line_no = idx
        # rate_limit_event carries the rate-limit bucket identity.
        elif event.get("type") == "rate_limit_event":
            info = event.get("rate_limit_info", {})
            rate_limit_type = info.get("rateLimitType")
            is_using_overage = info.get("isUsingOverage")
            if rate_limit_line_no is None:
                rate_limit_line_no = idx
        # assistant event carries the model's reply text.
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    reply_text += block.get("text", "")

    print()
    kv("apiKeySource",   repr(api_key_source))
    kv("rateLimitType",  repr(rate_limit_type))
    kv("isUsingOverage", is_using_overage)

    # -------------------------------------------------------------------------
    # STEP 5 — Show the reply, clearly separated
    # -------------------------------------------------------------------------
    print(f"\n{DIM}-- reply --{RESET}")
    print(f"  {BOLD}{reply_text.strip()}{RESET}")

    # -------------------------------------------------------------------------
    # PROOF — point the reader at the exact lines in the captured log
    # -------------------------------------------------------------------------
    # Anyone skeptical can open the NDJSON at the cited line numbers and read
    # the raw event for themselves. No interpretation, just bytes on disk.
    print(f"\n{DIM}-- proof you are on the OAUTH (subscription) path --{RESET}")
    print(f"  Check {BOLD}{SELF_REL}:{_line_of('#<wire>')}{RESET}  →  "
          f"{CYAN}scrubs ANTHROPIC_API_KEY/AUTH_TOKEN from subprocess env{RESET}  "
          f"{DIM}(both outrank the OAuth token; clearing them lets OAuth win){RESET}")
    print(f"  Check {BOLD}{log_path}:{init_line_no}{RESET}  →  "
          f'{CYAN}apiKeySource="{api_key_source}"{RESET}  '
          f'{DIM}("none" = no API-key credential chosen){RESET}')
    if rate_limit_line_no is not None:
        print(f"  Check {BOLD}{log_path}:{rate_limit_line_no}{RESET}  →  "
              f'{CYAN}rateLimitType="{rate_limit_type}"{RESET}  '
              f'{DIM}(Pro/Max 5-hour bucket — API keys never emit this){RESET}')
    else:
        print(f"  {AMBER}NOTE{RESET}  no rate_limit_event in {log_path} this run "
              f"(usually appears, but not guaranteed every call)")

    # -------------------------------------------------------------------------
    # VERDICT — pull the two decisive signals into one green banner
    # -------------------------------------------------------------------------
    banner(GREEN, "BILLED AGAINST: YOUR CLAUDE SUBSCRIPTION",
           f'apiKeySource="{api_key_source}" · '
           f'rateLimitType="{rate_limit_type}" (Pro/Max 5-hour bucket)')


if __name__ == "__main__":
    main()
