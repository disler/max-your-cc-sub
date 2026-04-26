# Maximize Your Claude Code Subscription (Without Getting BANNED)

> Let's answer the question: `Can I use my Claude subscription instead of an API key? I already paid for it so can I just... use it?`
>
> Watch the full [breakdown here](https://youtu.be/8IDzBRRFnQU).

![Anthropic Banned](assets/hero.png)

## The one rule

> **Your Pro/Max subscription is for your own individual use — the moment
> your code routes someone else's request through your seat, stop using
> the subscription OAuth token and switch to an API key.**

Two phrases to lock in.

1. **"Your own individual use"** is the permission Anthropic grants.
2. **"Someone else's request"** is the tripwire.

The moment another human is the intended user, you've crossed from individual use into separate-product territory. Paid, free, internal, or open-source: doesn't matter. If someone other than you is the intended beneficiary, you need an API key. Per the [legal clarification](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use) this is a Consumer Terms of Service violation, and Anthropic is actively enforcing it.

## 3 Tiers of usage

- ✅ Green (safe)
- ⚪ Gray (controversial)
- ❌ Red (bannable)

### ✅ Green (safe) usage

Anthropic explicitly endorses these cases, where you are the only human
whose work the runs are doing.

- Personal scripts on your own laptop: cron, dotfiles, pipelines
- Claude Agent SDK running *your own* agents and research
- CI on your own (individual) repo with `CLAUDE_CODE_OAUTH_TOKEN` as a secret
- Claude Code on your work laptop for engineering *you* author
- Claude Code Web and Claude Desktop on your subscription
- **One human, one subscription, one beneficiary**

> There's no risk here - this is where you should be deploying your subscription to SAVE TOKENS and CASH

### ⚪ Gray (controversial) usage

Cases Anthropic's wording leaves ambiguous, usually because more than one
human benefits from a single subscription. When in doubt, switch to an API
key or a Team/Enterprise seat.

- Agency or contractor work through your personal token
- Slack bots, daily reports used by multiple humans
- Open-source CLIs (only safe if every user brings their own token)
- Internal team tools running on one dev's Pro/Max token (risky)
- Third-party agent harnesses (OpenClaw-style), **HIGHLY contested**

> Honest move: grab an API key and stop guessing

### ❌ Red (bannable) usage

The practices Anthropic explicitly ruled out in the February 2026
[Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use)
clarification. These will get your account terminated.

- Shipping a product that runs on your Pro/Max OAuth token
- Multi-tenant SaaS logging users into Claude.ai on their behalf
- Pooling one subscription across a team (no Team/Enterprise seats)
- Reselling Claude access in any form: instant ban
- Extracting tokens from `~/.claude/.credentials.json` or Keychain

> Don't trade frontier AI access for a few hundred bucks

## Quickstart

### Agentic Quick Start

Clone the repo, open it in Claude Code (or any agentic coding tool), and run:

```
/install
```

That walks you through every prerequisite (`claude`, `just`, `uv`, `jq`),
helps you pick a credential path (OAuth vs API key), sets up `.env`, and
verifies the repo is ready — all interactively. If your tool doesn't
support slash commands, feed it `.claude/commands/install.md` as a prompt.
Then:

```
just oauth        # subscription-billed run (if you set up an OAuth token)
just api          # API-key run (if you set up an API key)
just compare      # run both and diff the auth signals side-by-side
```

### Manual Quick Start

```bash
# 1. Prereqs (one-time) — cross-platform: use brew / winget / apt equivalents
brew install just uv                             # macOS
#   or: winget install Casey.Just astral-sh.uv   # Windows
#   or: apt/dnf/pacman install just uv           # Linux
curl -fsSL https://claude.ai/install.sh | bash   # installs `claude`

# 2. Clone & enter
git clone <this-repo> max-your-cc-sub && cd max-your-cc-sub

# 3. Pick your credential(s)
cp .env.example .env
# For OAuth/subscription billing: run `claude setup-token` in a fresh
# terminal, paste the printed sk-ant-oat01-... into .env.
# For API-key billing: create one at https://console.anthropic.com/ and
# paste into .env as ANTHROPIC_API_KEY.

# 4. Sanity-check everything is wired up
just check

# 5. Run whichever flow you want
just oauth        # both CLI + SDK examples, subscription billing
just api          # both CLI + SDK examples, API-key billing
just compare      # run one of each and show the auth signals side-by-side
```

## What this codebase contains

Four tiny, heavily-commented examples that show `claude -p` and the Claude
Agent SDK (Python) running inference under two different billing paths:

| # | Example | Auth | Billing |
|---|---------|------|---------|
| 1 | `examples/01_oauth_cli.py` | `CLAUDE_CODE_OAUTH_TOKEN` | Your Claude Pro/Max subscription |
| 2 | `examples/02_oauth_sdk.py` | `CLAUDE_CODE_OAUTH_TOKEN` | Your Claude Pro/Max subscription |
| 3 | `examples/03_api_key_cli.py` | `ANTHROPIC_API_KEY` | Console API (per-token) |
| 4 | `examples/04_api_key_sdk.py` | `ANTHROPIC_API_KEY` | Console API (per-token) |

Every file is a PEP 723 single-file Python script (`uv run` resolves
dependencies on first run) and is commented line-by-line so you can read
top-to-bottom and understand exactly which flag, env var, or field is doing
what. Tested on macOS and Linux. Windows works via WSL or Git Bash — the
example scripts are portable Python, but the `just` recipes use POSIX
shell syntax.

Every example captures the Claude Code stream-json event feed and extracts
two fields that tell you — unambiguously — which credential is in use:

| Signal | OAuth (subscription) | API key |
|---|---|---|
| `system/init.apiKeySource` | `"none"` | `"ANTHROPIC_API_KEY"` |
| `rate_limit_event.rateLimitType` | `"five_hour"` (Pro/Max bucket) | *(no event emitted)* |

The `five_hour` rate-limit bucket is the decisive tell: API keys are billed
with RPM/TPM tiers and never emit a `five_hour` rate-limit event. If you see
it, you're on the subscription path.

> ### ⚠️ Silent-billing gotcha
>
> Claude Code's [credential precedence chain](https://code.claude.com/docs/en/authentication#authentication-precedence)
> puts `ANTHROPIC_API_KEY` (and `ANTHROPIC_AUTH_TOKEN`) **above**
> `CLAUDE_CODE_OAUTH_TOKEN`. If both are set in your shell, the API key wins
> silently — your run bills the API key while you think you're on the
> subscription. Every example in this repo scrubs `ANTHROPIC_API_KEY` /
> `ANTHROPIC_AUTH_TOKEN` from the subprocess environment before launching
> `claude`, so the OAuth path can win. If you wire this into your own
> scripts, do the same — and always read `apiKeySource` back from
> `system/init` to confirm.

## Repo layout

```
max-your-cc-sub/
├── README.md               # this file
├── LICENSE                 # MIT
├── justfile                # one-shot recipes
├── .env.example            # copy to .env and fill in credentials
├── examples/
│   ├── 01_oauth_cli.py     # OAuth via Claude Code CLI (spawns `claude -p`)
│   ├── 02_oauth_sdk.py     # OAuth via Claude Agent SDK
│   ├── 03_api_key_cli.py   # API key via Claude Code CLI
│   ├── 04_api_key_sdk.py   # API key via Claude Agent SDK
│   └── _compare_signals.py # helper for `just compare`
└── logs/                   # per-recipe captures (gitignored, overwritten each run)
    ├── check/status.txt
    ├── oauth-cli/events.ndjson
    ├── oauth-sdk/events.ndjson
    ├── api-cli/events.ndjson
    ├── api-sdk/events.ndjson
    └── compare/summary.txt
```

## Recipes (`just --list`)

```
default      # show this list
check        # verify prerequisites and credentials → logs/check/status.txt
oauth-setup  # run `claude setup-token` (interactive, needs a browser)
oauth-cli    # run example 1 (OAuth + CLI) → logs/oauth-cli/events.ndjson
oauth-sdk    # run example 2 (OAuth + SDK) → logs/oauth-sdk/events.ndjson
oauth        # run both OAuth examples in sequence
api-cli      # run example 3 (API key + CLI) → logs/api-cli/events.ndjson
api-sdk      # run example 4 (API key + SDK) → logs/api-sdk/events.ndjson
api          # run both API-key examples in sequence
compare      # run 1 OAuth + 1 API run → logs/compare/summary.txt
```

Every recipe writes into its own `logs/<recipe>/` directory and
overwrites on each run — no `clean` step needed.

## When to use which path

| Scenario | Use |
|---|---|
| Your own personal scripts on your own laptop | OAuth token |
| CI on your own GitHub repo | OAuth token (as a repo secret) |
| Claude Code on your machine for your work | OAuth token |
| Internal tool your team uses | API key (or Team/Enterprise plan) |
| SaaS / product / anything others use | **API key — always** |
| Open-source CLI you distribute | Instruct users to bring their own token |

## References

The official Anthropic surface — these are the documents that actually
govern what you can and can't do. If anything in this README disagrees
with these, the official pages win.

**Legal & policy**

- [Claude Code — Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)
- [Authentication and credential use](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use) — the Feb 2026 clarification that defines this whole question
- [Anthropic Consumer Terms of Service](https://www.anthropic.com/legal/consumer-terms)
- [Anthropic Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms)
- [Anthropic Usage Policy](https://www.anthropic.com/legal/aup)
- [Contact Anthropic Sales](https://www.anthropic.com/contact-sales) — the official place to ask about gray-zone use

**Authentication & credentials**

- [Authentication — Generate a long-lived token](https://code.claude.com/docs/en/authentication#generate-a-long-lived-token)
- [Authentication precedence chain](https://code.claude.com/docs/en/authentication#authentication-precedence) — why `ANTHROPIC_API_KEY` silently outranks `CLAUDE_CODE_OAUTH_TOKEN`

**Running Claude Code programmatically**

- [Run Claude Code programmatically (stream-json, verbose)](https://code.claude.com/docs/en/headless)
- [`system/init` event reference](https://code.claude.com/docs/en/headless#stream-responses) — where `apiKeySource` is documented
- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk)

**Rate limits (the `five_hour` signal)**

- [Manage extra usage for paid Claude plans](https://support.claude.com/en/articles/12429409-manage-extra-usage-for-paid-claude-plans) — Pro/Max five-hour rolling window
- [Our approach to rate limits for the Claude API](https://support.claude.com/en/articles/8243635-our-approach-to-rate-limits-for-the-claude-api)
- [API rate limits (RPM/TPM/monthly)](https://platform.claude.com/docs/en/api/rate-limits)
- [anthropics/claude-code #29300 — Expose rate limit utilization data in statusline JSON](https://github.com/anthropics/claude-code/issues/29300) — enumerates `rateLimitType` values

**Press & community**

- [The Register — Anthropic clarifies ban on third-party tool access (2026-02-20)](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)
- [VentureBeat — Anthropic cuts off Claude subscriptions with OpenClaw and third-party AI agents](https://venturebeat.com/technology/anthropic-cuts-off-the-ability-to-use-claude-subscriptions-with-openclaw-and)
- [weidwonder/claude_agent_sdk_oauth_demo](https://github.com/weidwonder/claude_agent_sdk_oauth_demo) — independent confirmation that the Agent SDK accepts `CLAUDE_CODE_OAUTH_TOKEN`

**Tooling**

- [PEP 723 — single-file Python scripts](https://peps.python.org/pep-0723/)
- [Astral `uv`](https://docs.astral.sh/uv/)
- [`just` — command runner](https://github.com/casey/just)

## Disclaimer

This repo is a technical walkthrough, not legal advice. Anthropic's terms
and enforcement posture change over time, and everything in here reflects
what the author observed as of April 2026. Before you ship anything that
depends on the subscription vs. API-key distinction:

1. **Go to the source.** The authoritative documents are
   [Claude Code — Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance),
   the [Consumer Terms of Service](https://www.anthropic.com/legal/consumer-terms),
   and the [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms).
   If this README and those pages disagree, the official pages win. They
   get updated; this file does not.
2. **When in doubt, ask or pay.** Contact
   [Anthropic sales](https://www.anthropic.com/contact-sales) for a
   definitive answer, or talk to your own counsel. An API key or a
   Team/Enterprise seat costs far less than an account termination or a
   ToS dispute.
3. **No lawyers were involved.** Nothing in this repo, the companion
   video, or any related content is legal advice. The author is a
   software engineer, not your attorney. You are solely responsible for
   your own compliance.

Use your head, read the real docs, and when the stakes are real, get
proper advice.
