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

- **Entrypoint 1 — Coding-Agent Native mode (`collect` + agent reasoning + `finalize`, zero LLM API key needed)**:
  Any coding agent (`Antigravity`, `Codex`, `Claude Code`, `Cursor`) can run real online collection with zero external LLM API key, act as the reasoning engine itself, and pass the draft JSON through the exact same Python Guard and report pipeline:
  1. `harness collect <app_name> [--github URL] [--url URL] [--local-app PATH --use-rea]` → outputs `reports/<app>.collected.json` (raw evidence + `prompt_contract`).
  2. Read `reports/<app>.collected.json`, extract 9 common + 5 specialized dimensions (with exact verbatim quotes copied from `collected_items`), architecture patterns, `user_reviews`, and `pm_guidance`, and write `reports/<app>.agent_draft.json`.
  3. `harness finalize reports/<app>.agent_draft.json` → runs `verify_all_dimensions()` Guard, generates Mermaid + `reports/<app>.intermediate.json` + `reports/<app>.md`, and updates SQLite cache (compatible with `harness compare` and `harness report`).
- **Entrypoint 2 — CLI API-key mode (autonomous pipeline)**: requires one LLM API key (`GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` in `.env` or environment). Optional `TAVILY_API_KEY` and `GITHUB_TOKEN` improve search speed and GitHub rate limits.
- **Offline benchmark mode (no API key needed)**: runs immediately using built-in curated benchmarks (`cursor`, `chatbi`, `perplexity`, `autogpt`).
- **Local ASAR / JS reverse engineering**: optional `--local-app <path> [--use-rea]` integrates `rea-agents` via Node.js (`npx -y rea-agents@latest`), automatically falling back to built-in scanning if Node/npx is unavailable.

## Core Commands

```bash
# Environment diagnostic
harness doctor

# Discover built-in registry apps
harness list
harness search <keyword>
harness info <app_name>

# Entrypoint 1: Coding-Agent Native (Zero API Key)
harness collect <app_name> --lang zh
# -> Agent reads reports/<app_name>.collected.json and writes reports/<app_name>.agent_draft.json
harness finalize reports/<app_name>.agent_draft.json

# Entrypoint 2: Autonomous CLI with API Key
harness analyze <app_name> --depth full --lang zh

# Entrypoint 2 (Offline curated benchmark)
harness analyze cursor --offline

# Custom sources or local unpacked Electron/JS app
harness analyze <app_name> --github <repo_url> --url <blog_url> --local-app </abs/path> --use-rea

# Compare multiple analyzed apps & inspect cache
harness compare cursor chatbi
harness report <app_name> --format json
harness cache list
```

## Dual-Entrypoint Sync Contract (Mandatory for Developers & Agents)

This repository maintains **two first-class user entrypoints** sharing `src/harness_analyzer/pipeline.py`:
1. Autonomous API CLI (`harness analyze`)
2. Coding-Agent Native CLI (`harness collect` -> Agent reasoning -> `harness finalize`)

**Whenever modifying collectors, dimensions, patterns, Guard rules, `IntermediateArtifact`, `PMGuidance`, `HarnessAnalysis`, cache, or report outputs**, you MUST update shared helpers in `pipeline.py` (or keep both `analyze` and `collect`/`finalize` synchronized) and verify parity in `tests/`.

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
- Also update `src/harness_analyzer/output/diagram.py`, `markdown.py`, and `comparison.py` together when changing report sections, ensuring every section keeps its Mermaid diagram reference and quantitative data evidence intact.
- Never attempt to bypass CAPTCHAs, Cloudflare challenges, or WAF blocks; `collectors/web_utils.py` trips a per-domain circuit breaker and records `blocked_sources` cleanly.
