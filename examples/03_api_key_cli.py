# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Example 3 — API key flow, using the Claude Code CLI (`claude -p`).

Cross-platform replacement for the old 03_api_key_cli.sh. Same script shape
as 01_oauth_cli.py, but authenticated with an API key from the Claude
Console (`sk-ant-api03-...`). Expect the opposite forensic signals:
`apiKeySource` becomes `"ANTHROPIC_API_KEY"` and no `rate_limit_event` with
`rateLimitType: "five_hour"` is emitted — that bucket is subscription-only.

Use this when you are building anything other humans will touch.

Run it:    just api-cli
Manually:  uv run examples/03_api_key_cli.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# --- Pretty output helpers (identical across all examples) -------------------
DIM, RESET, BOLD = "\033[2m", "\033[0m", "\033[1m"
CYAN, GREEN, AMBER, RED = "\033[1;36m", "\033[1;32m", "\033[1;33m", "\033[1;31m"

# Self-citation: the proof block prints `examples/<this-file>:<line>` pointing
# at the line tagged `#<wire>` below. Resolved at runtime so it doesn't rot.
SELF_REL = f"examples/{Path(__file__).name}"


def _line_of(marker: str) -> int:
    """Return the 1-based line number of the trailing-comment marker in this file.
    Requires the marker at end-of-line so doc-comment mentions don't collide."""
    for i, ln in enumerate(Path(__file__).read_text().splitlines(), 1):
        if ln.rstrip().endswith(marker):
            return i
    return 0


def kv(key: str, value: object, color: str = AMBER) -> None:
    print(f"  {BOLD}{key:<16}{RESET} {color}{value}{RESET}")


def banner(color: str, label: str, subtitle: str) -> None:
    bar = "═" * 62
    print(f"\n{color}{bar}{RESET}")
    print(f"{color}  {label}{RESET}")
    print(f"{DIM}  {subtitle}{RESET}")
    print(f"{color}{bar}{RESET}\n")


def dim(msg: str) -> None:
    print(f"{DIM}  {msg}{RESET}")


def main() -> None:
    # ----- Top banner (amber = API-key path) ---------------------------------
    banner(AMBER, "AUTH MODE: API KEY (CONSOLE / PER-TOKEN)",
           "Claude Code CLI · billing → your Console API account")

    # -------------------------------------------------------------------------
    # STEP 1 — Verify an API key is set (NOT an OAuth token)
    # -------------------------------------------------------------------------
    # API keys come from https://console.anthropic.com/ and start with
    # `sk-ant-api`. In -p / non-interactive mode, the key is always used
    # when present.
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print(f"{RED}FAIL{RESET}  ANTHROPIC_API_KEY is not set.")
        print("        Create one at https://console.anthropic.com/ → API Keys,")
        print("        then add it to .env as ANTHROPIC_API_KEY=sk-ant-api03-...")
        sys.exit(1)
    if api_key.startswith("sk-ant-oat"):
        print(f"{RED}FAIL{RESET}  That's an OAuth token, not an API key. "
              "Use 01_oauth_cli.py instead.")
        sys.exit(1)
    if not api_key.startswith("sk-ant-api"):
        print(f"{AMBER}WARN{RESET}  API key has an unrecognized prefix; continuing anyway.")
    dim(f"OK  API key prefix {api_key[:14]}…  (len={len(api_key)})")

    # -------------------------------------------------------------------------
    # STEP 2 — Clear the OAuth token for the subprocess
    # -------------------------------------------------------------------------
    # ANTHROPIC_API_KEY already outranks CLAUDE_CODE_OAUTH_TOKEN in the
    # precedence chain, so the API key would win either way. But clearing
    # the OAuth token makes intent unambiguous in the logs.
    env = os.environ.copy()
    if env.pop("CLAUDE_CODE_OAUTH_TOKEN", None):  #<wire>
        dim("OK  cleared CLAUDE_CODE_OAUTH_TOKEN for subprocess (unambiguous intent)")

    # -------------------------------------------------------------------------
    # STEP 3 — Run `claude -p`, identical to example 1
    # -------------------------------------------------------------------------
    # Per-recipe log dir, overwritten each run.
    log_dir = Path("logs") / "api-cli"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "events.ndjson"

    cmd = [
        "claude", "-p",
        "Reply with exactly these three words: api cli works",
        "--verbose",
        "--output-format", "stream-json",
        "--include-hook-events",
    ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    log_path.write_text(proc.stdout)
    if proc.returncode != 0:
        print(f"{RED}FAIL{RESET}  claude exited with code {proc.returncode}")
        sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)

    event_lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    dim(f"OK  captured {len(event_lines)} events → {log_path}")

    # -------------------------------------------------------------------------
    # STEP 4 — Extract signals (expect different values from example 1)
    # -------------------------------------------------------------------------
    # Expected:
    #   apiKeySource     = "ANTHROPIC_API_KEY"   (not "none")
    #   rate_limit_count = 0                     (API keys don't emit five_hour)
    api_key_source: str | None = None
    rate_limit_count: int = 0
    reply_text: str = ""
    # 1-based line number in events.ndjson where the system/init event lands —
    # that's the single decisive line for the API-key verdict.
    init_line_no: int | None = None

    for idx, line in enumerate(event_lines, start=1):
        event = json.loads(line)
        if event.get("type") == "system" and event.get("subtype") == "init":
            api_key_source = event.get("apiKeySource")
            init_line_no = idx
        elif event.get("type") == "rate_limit_event":
            rate_limit_count += 1
        elif event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    reply_text += block.get("text", "")

    print()
    kv("apiKeySource",      repr(api_key_source))
    kv("rate_limit_events", f"{rate_limit_count}  (expected 0 — API keys don't emit five_hour)")

    # -------------------------------------------------------------------------
    # STEP 5 — Show the reply
    # -------------------------------------------------------------------------
    print(f"\n{DIM}-- reply --{RESET}")
    print(f"  {BOLD}{reply_text.strip()}{RESET}")

    # -------------------------------------------------------------------------
    # PROOF — point the reader at the exact line that closes the case
    # -------------------------------------------------------------------------
    # For the API-key path, the verdict rests on one positive line and one
    # negative observation: apiKeySource flips to "ANTHROPIC_API_KEY", AND
    # the file contains zero rate_limit_event entries (subscription-only).
    print(f"\n{DIM}-- proof you are on the API-KEY (console) path --{RESET}")
    print(f"  Check {BOLD}{SELF_REL}:{_line_of('#<wire>')}{RESET}  →  "
          f"{AMBER}clears CLAUDE_CODE_OAUTH_TOKEN from subprocess env{RESET}  "
          f"{DIM}(makes the API-key path unambiguous in the logs){RESET}")
    if init_line_no is not None:
        print(f"  Check {BOLD}{log_path}:{init_line_no}{RESET}  →  "
              f'{AMBER}apiKeySource="{api_key_source}"{RESET}  '
              f'{DIM}(the API key won the credential precedence chain){RESET}')
    print(f"  Check {BOLD}{log_path}{RESET}  →  "
          f'{AMBER}{rate_limit_count} rate_limit_event entries{RESET}  '
          f'{DIM}(expected 0 — API keys never emit "five_hour"){RESET}')

    # -------------------------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------------------------
    banner(GREEN, "BILLED AGAINST: YOUR CONSOLE API ACCOUNT",
           f'apiKeySource="{api_key_source}" · '
           f'per-token pricing · safe for products')


if __name__ == "__main__":
    main()
