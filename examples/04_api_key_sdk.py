# /// script
# requires-python = ">=3.11"
# dependencies = ["claude-agent-sdk>=0.1.0"]
# ///
"""
Example 4 — API key flow, using the Claude Agent SDK (Python).

Goal: Same SDK script as Example 2, but authenticated with an API key instead
of an OAuth token. This is what you should use when you're building products,
services, internal team tooling, or anything other humans will end up using.

Run it:    just api-sdk
Manually:  uv run examples/04_api_key_sdk.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import AssistantMessage, ResultMessage, SystemMessage, TextBlock


# --- Pretty output helpers (ANSI colors, no deps) ----------------------------
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


def precheck() -> None:
    """Require an API key and refuse to run if OAuth creds are also present."""
    # API keys from https://console.anthropic.com/ start with `sk-ant-api03-`.
    # They bill against the Console project (per-token pricing), NOT any
    # Claude.ai subscription.
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key.startswith("sk-ant-api"):
        sys.exit("FAIL: ANTHROPIC_API_KEY missing or wrong prefix. "
                 "Create one at https://console.anthropic.com/.")
    # Clear the OAuth token so this run is unambiguously on the API-key path.
    # (ANTHROPIC_API_KEY already has higher precedence than
    # CLAUDE_CODE_OAUTH_TOKEN, but clearing makes intent obvious in logs.)
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("NOTE: CLAUDE_CODE_OAUTH_TOKEN was set; ignoring for this run.")
        os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    print(f"OK  API key prefix {api_key[:14]}…, len={len(api_key)}")


async def main() -> None:
    banner(AMBER, "AUTH MODE: API KEY (CONSOLE / PER-TOKEN)",
           "Claude Agent SDK · billing → your Console API account")
    precheck()

    # Configure the run. Unlike the OAuth example, we pass the API key
    # through to the spawned Claude Code subprocess. Everything else about
    # the SDK call is identical — that's the whole point.
    options = ClaudeAgentOptions(
        env={"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]},  #<wire>
        max_turns=1,
        allowed_tools=[],
    )

    # Per-recipe log dir, overwritten each run.
    log_dir = Path("logs") / "api-sdk"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "events.ndjson"
    log_lines: list[str] = []

    api_key_source: str | None = None
    rate_limit_count: int = 0
    reply_text: str = ""
    # 1-based line number in events.ndjson where the system/init message lands.
    init_line_no: int | None = None

    async for msg in query(
        prompt="Reply with exactly these three words: api sdk works",
        options=options,
    ):
        # system/init — apiKeySource should be "ANTHROPIC_API_KEY" this time.
        if isinstance(msg, SystemMessage):
            data = msg.data or {}
            print(f"\n{DIM}-- system/{msg.subtype} --{RESET}")
            kv("session_id",   data.get("session_id"))
            kv("model",        data.get("model"))
            kv("apiKeySource", repr(data.get("apiKeySource")))
            api_key_source = data.get("apiKeySource")
            log_lines.append(json.dumps({"msg_type": "SystemMessage",
                                         "subtype": msg.subtype, **data}))
            if msg.subtype == "init" and init_line_no is None:
                init_line_no = len(log_lines)

        # assistant — the model's text reply
        elif isinstance(msg, AssistantMessage):
            chunks: list[str] = []
            for block in msg.content:
                if isinstance(block, TextBlock):
                    reply_text += block.text
                    chunks.append(block.text)
            log_lines.append(json.dumps({"msg_type": "AssistantMessage",
                                         "text": "".join(chunks)}))

        # result — final usage / cost / timing
        elif isinstance(msg, ResultMessage):
            print(f"\n{DIM}-- result --{RESET}")
            kv("duration_ms",   msg.duration_ms)
            kv("input_tokens",  (msg.usage or {}).get("input_tokens"))
            kv("output_tokens", (msg.usage or {}).get("output_tokens"))
            kv("total_cost_usd", f"${msg.total_cost_usd}  {DIM}(standard API pricing applies){RESET}")
            log_lines.append(json.dumps({
                "msg_type": "ResultMessage",
                "session_id": msg.session_id,
                "is_error": msg.is_error,
                "duration_ms": msg.duration_ms,
                "total_cost_usd": msg.total_cost_usd,
                "usage": msg.usage,
            }))

        # anything else — API-key runs usually omit RateLimitEvent entirely.
        else:
            cls_name = type(msg).__name__
            if cls_name == "RateLimitEvent":
                rate_limit_count += 1
            print(f"\n{DIM}-- {cls_name} --{RESET}\n  {DIM}{msg!r}{RESET}")
            log_lines.append(json.dumps({"msg_type": cls_name, "repr": repr(msg)[:500]}))

    log_path.write_text("\n".join(log_lines) + "\n")

    print(f"\n{DIM}-- reply --{RESET}")
    print(f"  {BOLD}{reply_text.strip()}{RESET}")

    # Proof — point the reader at the exact line that closes the case
    # AND at the line in this file that wired the credential.
    print(f"\n{DIM}-- proof you are on the API-KEY (console) path --{RESET}")
    print(f"  Check {BOLD}{SELF_REL}:{_line_of('#<wire>')}{RESET}  →  "
          f"{AMBER}explicit API-key handoff to the SDK subprocess via "
          f"ClaudeAgentOptions(env=...){RESET}")
    if init_line_no is not None:
        print(f"  Check {BOLD}{log_path}:{init_line_no}{RESET}  →  "
              f'{AMBER}apiKeySource="{api_key_source}"{RESET}  '
              f'{DIM}(the API key won the credential precedence chain){RESET}')
    print(f"  Check {BOLD}{log_path}{RESET}  →  "
          f'{AMBER}{rate_limit_count} RateLimitEvent entries{RESET}  '
          f'{DIM}(expected 0 — API keys never emit "five_hour"){RESET}')

    banner(GREEN, "BILLED AGAINST: YOUR CONSOLE API ACCOUNT",
           f'apiKeySource={api_key_source!r} · rate_limit_events={rate_limit_count} '
           f'· per-token pricing · safe for products · logged to {log_path}')


if __name__ == "__main__":
    asyncio.run(main())
