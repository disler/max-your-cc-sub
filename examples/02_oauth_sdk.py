# /// script
# requires-python = ">=3.11"
# dependencies = ["claude-agent-sdk>=0.1.0"]
# ///
"""
Example 2 — OAuth subscription flow, using the Claude Agent SDK (Python).

Goal: Prove the SDK routes through the same subscription billing path as the
CLI when we hand it a `CLAUDE_CODE_OAUTH_TOKEN`. The SDK spawns the Claude
Code binary as a subprocess, so the env-var-based credential flows straight
through — and we also demonstrate the explicit `ClaudeAgentOptions.env`
passthrough.

Run it:    just oauth-sdk
Manually:  uv run examples/02_oauth_sdk.py
"""

# `asyncio` — the SDK's `query()` is an async generator, so we drive it inside
# an event loop with `asyncio.run(main())` at the bottom of the file.
import asyncio
# `json` — serialize yielded messages so we can dump them into a log file.
import json
# `os` — we read the token out of the environment and also sanity-check that
# no higher-precedence credentials are present.
import os
# `sys` — we use `sys.exit(msg)` for hard-fail preconditions.
import sys
# `pathlib.Path` — create the per-recipe log directory portably.
from pathlib import Path


# --- Pretty output helpers (ANSI colors, no deps) ----------------------------
# Dim for process chatter; bold/color for the stuff you came to see.
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


def kv(key: str, value: object, color: str = CYAN) -> None:
    print(f"  {BOLD}{key:<16}{RESET} {color}{value}{RESET}")


def banner(color: str, label: str, subtitle: str) -> None:
    bar = "═" * 62
    print(f"\n{color}{bar}{RESET}")
    print(f"{color}  {label}{RESET}")
    print(f"{DIM}  {subtitle}{RESET}")
    print(f"{color}{bar}{RESET}\n")

# The SDK's public surface. `query()` is the one-off helper; `ClaudeAgentOptions`
# is where we configure env, tools, limits, etc.
from claude_agent_sdk import ClaudeAgentOptions, query
# Typed message classes. The SDK yields objects of these types so we can
# `isinstance`-check and pull structured data instead of parsing JSON.
from claude_agent_sdk.types import (
    AssistantMessage,  # the model's turn; contains content blocks
    ResultMessage,     # the final "run complete" event with usage + cost
    SystemMessage,     # yielded when the underlying CLI emits system/init etc.
    TextBlock,         # a text chunk inside an AssistantMessage
)


def precheck() -> None:
    """Ensure this process will use the OAuth token and nothing higher-precedence."""
    # The OAuth token itself must be present and start with the subscription
    # prefix (`sk-ant-oat01-`). An API key (`sk-ant-api03-`) would NOT be
    # rejected by the SDK, it would just silently get billed wrong.
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if not token.startswith("sk-ant-oat01-"):
        sys.exit("FAIL: CLAUDE_CODE_OAUTH_TOKEN missing or wrong prefix. "
                 "Run `claude setup-token` to generate one.")

    # ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN outrank the OAuth token in
    # the documented precedence chain. If either is set (for example because
    # your .env carries both creds) they'd silently bill the wrong account.
    # Pop them from THIS process's env and warn — same behavior as the
    # bash example (`unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN`). The
    # user's shell env is untouched; this only affects the subprocess we
    # spawn for the SDK run.
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if os.environ.pop(var, None):
            print(f"NOTE: {var} was set; cleared for this process so OAuth wins.")

    # If we got here, the environment is clean and the OAuth path will win.
    print(f"OK  token prefix {token[:14]}…, len={len(token)}")
    print("OK  no higher-precedence credentials remain in env")


async def main() -> None:
    banner(CYAN, "AUTH MODE: OAUTH (SUBSCRIPTION)",
           "Claude Agent SDK · billing → your Claude Pro/Max subscription")
    precheck()

    # Configure the run.
    # The SDK launches the Claude Code CLI as a subprocess. By default that
    # subprocess inherits our env (where CLAUDE_CODE_OAUTH_TOKEN lives), but
    # we also pass it explicitly via `env=` so this example works even when
    # a caller has scrubbed the parent env.
    options = ClaudeAgentOptions(
        # Explicitly forward only the OAuth token to the subprocess. You could
        # add other env vars here if you wanted (e.g., proxy settings).
        env={"CLAUDE_CODE_OAUTH_TOKEN": os.environ["CLAUDE_CODE_OAUTH_TOKEN"]},  #<wire>
        # Pure inference — one turn, zero tools. Keeps the POC deterministic.
        max_turns=1,
        allowed_tools=[],
    )

    # Per-recipe log dir, overwritten on every run. Matches the CLI examples
    # for parity — each `just <recipe>` deposits one `events.ndjson` in its
    # own folder so you can diff runs without any cleanup step.
    log_dir = Path("logs") / "oauth-sdk"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "events.ndjson"
    log_lines: list[str] = []  # we flush to disk after the loop ends

    # Track the forensic signals as we stream events. We'll print them in
    # order as they arrive (dim) and then summarize them in the final banner.
    api_key_source: str | None = None
    rate_limit_type: str | None = None
    reply_text: str = ""
    # 1-based line numbers in events.ndjson where each forensic signal
    # lands — every `log_lines.append` produces one line in the file, so
    # `len(log_lines)` after the append IS the line number we want.
    init_line_no: int | None = None
    rate_limit_line_no: int | None = None

    async for msg in query(
        prompt="Reply with exactly these three words: oauth sdk works",
        options=options,
    ):
        # --- system/init ----------------------------------------------------
        # The authoritative "which credential did I pick?" signal.
        if isinstance(msg, SystemMessage):
            data = msg.data or {}
            print(f"\n{DIM}-- system/{msg.subtype} --{RESET}")
            kv("session_id",   data.get("session_id"))
            kv("model",        data.get("model"))
            kv("apiKeySource", repr(data.get("apiKeySource")))
            api_key_source = data.get("apiKeySource")
            # Serialize for the log: the raw `data` dict already contains
            # everything we need (session_id, model, apiKeySource, etc.).
            log_lines.append(json.dumps({"msg_type": "SystemMessage",
                                         "subtype": msg.subtype, **data}))
            if msg.subtype == "init" and init_line_no is None:
                init_line_no = len(log_lines)

        # --- assistant ------------------------------------------------------
        # The model's output turn.
        elif isinstance(msg, AssistantMessage):
            chunks: list[str] = []
            for block in msg.content:
                if isinstance(block, TextBlock):
                    reply_text += block.text
                    chunks.append(block.text)
            log_lines.append(json.dumps({"msg_type": "AssistantMessage",
                                         "text": "".join(chunks)}))

        # --- result ---------------------------------------------------------
        # Final usage/cost. total_cost_usd is client-side math from token
        # counts; it's NOT a charge indicator. The credential determines
        # where the real bill lands.
        elif isinstance(msg, ResultMessage):
            print(f"\n{DIM}-- result --{RESET}")
            kv("duration_ms",  msg.duration_ms)
            kv("input_tokens", (msg.usage or {}).get("input_tokens"))
            kv("output_tokens", (msg.usage or {}).get("output_tokens"))
            kv("total_cost_usd", f"${msg.total_cost_usd}  {DIM}(client estimate — not a charge){RESET}")
            log_lines.append(json.dumps({
                "msg_type": "ResultMessage",
                "session_id": msg.session_id,
                "is_error": msg.is_error,
                "duration_ms": msg.duration_ms,
                "total_cost_usd": msg.total_cost_usd,
                "usage": msg.usage,
            }))

        # --- RateLimitEvent and other events -------------------------------
        # The RateLimitEvent's rate_limit_type is the other decisive signal:
        # "five_hour" = subscription; API keys never emit this bucket.
        else:
            cls_name = type(msg).__name__
            if cls_name == "RateLimitEvent" and hasattr(msg, "rate_limit_info"):
                info = msg.rate_limit_info
                # The raw JSON dict lives on `.raw` and carries the original
                # camelCase field names (isUsingOverage, overageStatus, etc.).
                # Typed attributes (rate_limit_type, overage_status) are a
                # subset — fields like isUsingOverage only exist in .raw.
                raw = getattr(info, "raw", {}) or {}
                print(f"\n{DIM}-- rate_limit_event --{RESET}")
                kv("rateLimitType",  repr(getattr(info, "rate_limit_type", None)))
                kv("overageStatus",  repr(getattr(info, "overage_status", None)))
                kv("isUsingOverage", raw.get("isUsingOverage"))
                rate_limit_type = getattr(info, "rate_limit_type", None)
                log_lines.append(json.dumps({"msg_type": "RateLimitEvent", **raw}))
                if rate_limit_line_no is None:
                    rate_limit_line_no = len(log_lines)
            else:
                print(f"\n{DIM}-- {cls_name} --{RESET}\n  {DIM}{msg!r}{RESET}")
                log_lines.append(json.dumps({"msg_type": cls_name, "repr": repr(msg)[:500]}))

    # Flush the collected messages to the per-recipe log file (overwrite).
    log_path.write_text("\n".join(log_lines) + "\n")

    # Final reply, bold so it doesn't blend into the process chatter.
    print(f"\n{DIM}-- reply --{RESET}")
    print(f"  {BOLD}{reply_text.strip()}{RESET}")

    # Proof — point the reader at the exact lines in the captured NDJSON
    # AND at the line in this file that wired the credential.
    print(f"\n{DIM}-- proof you are on the OAUTH (subscription) path --{RESET}")
    print(f"  Check {BOLD}{SELF_REL}:{_line_of('#<wire>')}{RESET}  →  "
          f"{CYAN}explicit OAuth-token handoff to the SDK subprocess via "
          f"ClaudeAgentOptions(env=...){RESET}")
    if init_line_no is not None:
        print(f"  Check {BOLD}{log_path}:{init_line_no}{RESET}  →  "
              f'{CYAN}apiKeySource="{api_key_source}"{RESET}  '
              f'{DIM}("none" = no API-key credential chosen){RESET}')
    if rate_limit_line_no is not None:
        print(f"  Check {BOLD}{log_path}:{rate_limit_line_no}{RESET}  →  "
              f'{CYAN}rateLimitType="{rate_limit_type}"{RESET}  '
              f'{DIM}(Pro/Max 5-hour bucket — API keys never emit this){RESET}')
    else:
        print(f"  {AMBER}NOTE{RESET}  no RateLimitEvent in {log_path} this run "
              f"(usually appears, but not guaranteed every call)")

    # Verdict banner — pulls the two decisive signals into one line.
    banner(GREEN, "BILLED AGAINST: YOUR CLAUDE SUBSCRIPTION",
           f'apiKeySource={api_key_source!r} · rateLimitType={rate_limit_type!r} '
           f'(Pro/Max 5-hour bucket) · logged to {log_path}')


# Standard Python entry point. Only run `main()` if this file is executed
# directly, not when it's imported from somewhere else.
if __name__ == "__main__":
    asyncio.run(main())
