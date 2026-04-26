# justfile — one-shot commands for max-your-cc-sub
# Install just:  brew install just  (macOS/Linux)  |  winget install Casey.Just  (Windows)
# See recipes:   just        (or: just --list)

# Auto-load .env so CLAUDE_CODE_OAUTH_TOKEN / ANTHROPIC_API_KEY flow through.
set dotenv-load := true

# Show all recipes.
default:
    @just --list

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

# Print prerequisite status (claude, uv, token, api key). Saves a copy to logs/check/status.txt.
check:
    @mkdir -p logs/check
    @{ \
      echo "---- prerequisites ----"; \
      command -v claude >/dev/null && echo "claude:   $(claude --version 2>&1 | head -1)" || echo "claude:   MISSING (install: https://claude.ai/install.sh)"; \
      command -v uv >/dev/null && echo "uv:       $(uv --version)" || echo "uv:       MISSING (install: brew install uv)"; \
      command -v just >/dev/null && echo "just:     $(just --version)" || echo "just:     MISSING (install: brew install just)"; \
      echo "---- credentials ----"; \
      [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && echo "OAuth:    set (${CLAUDE_CODE_OAUTH_TOKEN:0:14}...)" || echo "OAuth:    NOT SET  (run: just oauth-setup)"; \
      [ -n "${ANTHROPIC_API_KEY:-}" ] && echo "API key:  set (${ANTHROPIC_API_KEY:0:14}...)" || echo "API key:  NOT SET  (export ANTHROPIC_API_KEY=...)"; \
    } | tee logs/check/status.txt

# Generate a long-lived OAuth token for subscription billing.
# Opens a browser. Needs a real terminal — not runnable inside another agent.
oauth-setup:
    @echo "Opening Anthropic OAuth flow. Copy the printed sk-ant-oat01-... token"
    @echo "and add it to .env as:   CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-..."
    claude setup-token

# -----------------------------------------------------------------------------
# OAuth (subscription billing) — for YOUR OWN individual use only.
# Forbidden: shipping this in a product/tool/service used by others.
# -----------------------------------------------------------------------------

# Run the CLI example with the OAuth token (spawns `claude -p`, captures stream-json).
oauth-cli:
    uv run examples/01_oauth_cli.py

# Run the Agent SDK example with the OAuth token.
oauth-sdk:
    uv run examples/02_oauth_sdk.py

# Run both OAuth examples in sequence.
oauth: oauth-cli oauth-sdk

# -----------------------------------------------------------------------------
# API key (Commercial Terms) — the path for products, services, team tools.
# -----------------------------------------------------------------------------

# Run the CLI example with the API key (spawns `claude -p`, captures stream-json).
api-cli:
    uv run examples/03_api_key_cli.py

# Run the Agent SDK example with the API key.
api-sdk:
    uv run examples/04_api_key_sdk.py

# Run both API-key examples in sequence.
api: api-cli api-sdk

# -----------------------------------------------------------------------------
# Verification / comparison
# -----------------------------------------------------------------------------

# Run one OAuth + one API-key run and print the auth signals side-by-side.
# Saves a plain-text summary to logs/compare/summary.txt.
compare: oauth-cli api-cli
    uv run examples/_compare_signals.py

# -----------------------------------------------------------------------------
# Interactive helpers
# -----------------------------------------------------------------------------

# Boot Claude Code in dangerous mode and run /prime in interactive mode.
prime:
    claude --dangerously-skip-permissions "/prime"
