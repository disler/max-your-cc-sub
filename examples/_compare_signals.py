# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Helper for `just compare` — reads the two stream-json logs captured by
01_oauth_cli.py and 03_api_key_cli.py and prints the auth signals side-by-
side. Pure stdlib, cross-platform.
"""

import json
import sys
from pathlib import Path

DIM, RESET, BOLD = "\033[2m", "\033[0m", "\033[1m"
CYAN, AMBER, GREEN = "\033[1;36m", "\033[1;33m", "\033[1;32m"

CASES = [
    ("OAuth run   (subscription)", "logs/oauth-cli/events.ndjson", CYAN),
    ("API-key run (console)",      "logs/api-cli/events.ndjson", AMBER),
]

# Where we persist the formatted comparison output for later review.
COMPARE_OUT = Path("logs/compare/summary.txt")


def summarize(path: str) -> tuple[str | None, int, int, str | None, int | None]:
    """Return (apiKeySource, init_line_no, rate_limit_event_count, rate_limit_type, rate_limit_line_no)."""
    lines = [ln for ln in Path(path).read_text().splitlines() if ln.strip()]
    api_key_source: str | None = None
    init_line_no: int = 0
    rl_count: int = 0
    rl_type: str | None = None
    rl_line_no: int | None = None
    for idx, ln in enumerate(lines, start=1):
        ev = json.loads(ln)
        if ev.get("type") == "system" and ev.get("subtype") == "init" and not init_line_no:
            api_key_source = ev.get("apiKeySource")
            init_line_no = idx
        elif ev.get("type") == "rate_limit_event":
            rl_count += 1
            if rl_line_no is None:
                rl_type = ev.get("rate_limit_info", {}).get("rateLimitType")
                rl_line_no = idx
    return api_key_source, init_line_no, rl_count, rl_type, rl_line_no


def main() -> None:
    # Render once with color (to the terminal) and once plain (to the log
    # file) so the persisted summary is readable without ANSI escapes.
    plain_lines: list[str] = ["Auth signals, side-by-side",
                              "─" * 62]

    print(f"\n{BOLD}Auth signals, side-by-side{RESET}")
    print("─" * 62)
    for label, path, color in CASES:
        if not Path(path).exists():
            print(f"{color}{label}{RESET}  {DIM}(missing: {path}){RESET}")
            plain_lines.append(f"{label}  (missing: {path})")
            continue
        api_src, init_ln, rl_count, rl_type, rl_ln = summarize(path)
        print(f"{color}{label}{RESET}")
        print(f"  {BOLD}{'apiKeySource':<16}{RESET} {color}{api_src!r}{RESET}  "
              f"{DIM}← {path}:{init_ln}{RESET}")
        rl_loc = f"{path}:{rl_ln}" if rl_ln else f"{path} (no entries)"
        print(f"  {BOLD}{'rate_limit_events':<16}{RESET} {color}{rl_count}  "
              f"{DIM}(type={rl_type!r}, ← {rl_loc}){RESET}")
        print()
        plain_lines += [
            label,
            f"  apiKeySource      {api_src!r}    proof: {path}:{init_ln}",
            f"  rate_limit_events {rl_count}  (type={rl_type!r})    proof: {rl_loc}",
            "",
        ]

    print(f"{GREEN}{BOLD}Reminder:{RESET} rateLimitType = \"five_hour\" is the decisive")
    print("  subscription tell. API keys never emit it. Open the cited")
    print("  file:line pairs above to read the raw event for yourself.\n")
    plain_lines.append('Reminder: rateLimitType = "five_hour" is the decisive '
                       'subscription tell. API keys never emit it. Open the cited '
                       'file:line pairs above to read the raw event for yourself.')

    # Persist the plain-text summary into logs/compare/ for later review.
    COMPARE_OUT.parent.mkdir(parents=True, exist_ok=True)
    COMPARE_OUT.write_text("\n".join(plain_lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
