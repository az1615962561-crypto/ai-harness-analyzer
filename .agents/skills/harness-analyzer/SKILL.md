---
name: harness-analyzer
description: Analyze the underlying Harness architecture of any AI application (Agent orchestration, model routing, tool chains, context/RAG, sandbox, human-in-the-loop UX) and generate PM-ready MVP guidance and structured JSON/Markdown artifacts. Use when asked to research, benchmark, compare, or reverse-engineer how an AI product works under the hood.
---

# AI Harness Analyzer Skill

Use this skill whenever an agent needs to research an AI product's engineering architecture or generate a Product Manager / Architect benchmark report from this repository.

## Workflow

1. **Check environment**: Ensure the project is installed (`harness --help` or `.venv/bin/harness --help`). If not installed, run `pip install -e .` (or `uv pip install -e .`).
2. **Check registry & existing benchmarks**:
   ```bash
   harness list
   harness info <app_name>
   ```
3. **Run analysis**:
   - **Zero-API-key curated benchmark** (`cursor`, `chatbi`, `perplexity`, `autogpt`):
     ```bash
     harness analyze <app_name> --offline
     ```
   - **Live online deep analysis** (works for any app, including unknown niche products; requires `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY`):
     ```bash
     harness analyze <app_name> --depth full --lang zh
     ```
   - **Local Electron ASAR / unpacked JS reverse engineering** (auto-uses `rea-agents` if Node.js is available, otherwise built-in scanner):
     ```bash
     harness analyze <app_name> --local-app /absolute/path/to/app_or_asar --use-rea
     ```
4. **Consume structured deliverables**:
   - Read `reports/<app_name>.intermediate.json` for machine-readable facts, per-dimension `coupling_level` / `guard_status`, `search_coverage`, and `user_reviews`.
   - Read `reports/<app_name>.md` for the PM Solution Guidance layer, Mermaid topology diagram, and 9+5 dimension analysis.
5. **Cross-app comparison**:
   ```bash
   harness compare <app1> <app2>
   ```

## Guardrails

- Respect `guard_status` in `reports/<app_name>.intermediate.json`: never present `unverified_capped` (1–2 star inferred) dimensions as confirmed architecture facts.
- Report any `blocked_sources` (Cloudflare/CAPTCHA/403/429) transparently; do not attempt to bypass anti-bot challenges.
