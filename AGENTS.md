# AGENTS.md — Universal Agent Guide for AI Harness Analyzer

This repository is designed to be **agent-agnostic and ready to use out of the box** by any coding agent (`Codex`, `Claude Code`, `Cursor`, `Antigravity`, `Gemini CLI`, `OpenHands`, etc.) or human developer.

## What This Project Does

`harness-analyzer` deconstructs the engineering **Harness Architecture** behind AI applications (Agent orchestration, model routing, tool chains, prompts, context engineering, sandboxing, human-in-the-loop UX, and product-level MVP guidance).

## Quick Setup for Agents

```bash
# Python 3.11+ required
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
# Or standard pip:
# python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```

- **Offline benchmark mode (no API key needed)**: runs immediately using built-in curated benchmarks (`cursor`, `chatbi`, `perplexity`, `autogpt`).
- **Online analysis mode**: requires one LLM API key (`GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` in `.env` or environment). Optional `TAVILY_API_KEY` and `GITHUB_TOKEN` improve search speed and GitHub rate limits.
- **Local ASAR / JS reverse engineering**: optional `--local-app <path> [--use-rea]` integrates `rea-agents` via Node.js (`npx -y rea-agents@latest`), automatically falling back to built-in scanning if Node/npx is unavailable.

## Core Commands

```bash
# Discover built-in registry apps
harness list
harness search <keyword>
harness info <app_name>

# Analyze an app (offline curated benchmark)
harness analyze cursor --offline

# Analyze any app online (registry app or brand-new niche app)
harness analyze <app_name> --depth full --lang zh

# Analyze with custom sources or local unpacked Electron/JS app
harness analyze <app_name> --github <repo_url> --url <blog_url> --local-app </abs/path> --use-rea

# Compare multiple analyzed apps
harness compare cursor chatbi

# Read cached output (markdown or json)
harness report <app_name> --format json
```

## Outputs & Artifacts to Inspect

After running `harness analyze <app_name>`, read these files:
1. `reports/<app_name>.intermediate.json` — Structured intermediate artifact containing:
   - Coupling-tiered, individually guarded dimensions (`CORE` / `MODERATE` / `LOOSE`, with `guard_status` and `verbatim_quotes`)
   - Bilingual search coverage report (`SearchCoverageReport`) + `blocked_sources`
   - Authoritative community `user_reviews` (Hacker News, GitHub Issues, Reddit/G2/Zhihu)
2. `reports/<app_name>.md` — Final 3-layer report (PM Solution Guidance → Intermediate Artifact & User Reviews → 9+5 Technical Dimension Breakdown → Source Traceability).

## Repository Conventions & Testing

- Source root: `src/harness_analyzer/`
- Registry data: `src/harness_analyzer/registry/apps.yaml`
- Cross-agent skill instructions: `.agents/skills/harness-analyzer/SKILL.md`
- Always verify changes with:
  ```bash
  pytest -v tests/
  ```
- Never attempt to bypass CAPTCHAs, Cloudflare challenges, or WAF blocks; `collectors/web_utils.py` trips a per-domain circuit breaker and records `blocked_sources` cleanly.
