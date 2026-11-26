---
name: harness-analyzer
description: Analyze the underlying Harness architecture of any AI application (Agent orchestration, model routing, tool chains, context/RAG, sandbox, human-in-the-loop UX) and generate PM-ready MVP guidance and structured JSON/Markdown artifacts. Use when asked to research, benchmark, compare, or reverse-engineer how an AI product works under the hood.
---

# AI Harness Analyzer Skill

Use this skill whenever an agent needs to research an AI product's engineering architecture or generate a Product Manager / Architect benchmark report from this repository.

## Workflow (Dual Entrypoints)

1. **Check environment**: Ensure the project is installed (`harness --help` or `.venv/bin/harness --help`) and inspect `harness doctor`. If not installed, run `pip install -e .` (or `uv pip install -e .`).
2. **Check registry & existing benchmarks**:
   ```bash
   harness list
   harness info <app_name>
   ```
3. **Choose the right analysis entrypoint**:
   - **Entrypoint A — Coding-Agent Native mode (RECOMMENDED when running inside an agent without external LLM API keys)**:
     1. Run live 5-channel collection (zero API key required):
        ```bash
        harness collect <app_name> --lang zh
        ```
     2. Read `reports/<app_name>.collected.json` completely (`collected_items`, `search_coverage`, and `prompt_contract`).
     3. Act as the analysis engine yourself and write `reports/<app_name>.agent_draft.json` conforming strictly to `prompt_contract.expected_draft_schema` (choosing the matching 5 `specialized_dimensions_by_category[category]` keys and copying exact `verbatim_quotes` from `collected_items`).
     4. Run the Python Guard, cache persistence, and report builder:
        ```bash
        harness finalize reports/<app_name>.agent_draft.json
        ```
   - **Entrypoint B — Autonomous CLI mode (when an LLM API key is configured)**:
     ```bash
     harness analyze <app_name> --depth full --lang zh
     ```
   - **Zero-API-key curated offline benchmark** (`cursor`, `chatbi`, `perplexity`, `autogpt`):
     ```bash
     harness analyze <app_name> --offline
     ```
   - **Local Electron ASAR / unpacked JS reverse engineering** (works with both `collect` and `analyze`; auto-uses `rea-agents` if Node.js is available):
     ```bash
     harness collect <app_name> --local-app /absolute/path/to/app_or_asar --use-rea
     ```
4. **Consume structured deliverables**:
   - Read `reports/<app_name>.intermediate.json` for machine-readable facts, per-dimension `coupling_level` / `guard_status`, `search_coverage`, and `user_reviews`.
   - Read `reports/<app_name>.md` for the PM Solution Guidance layer, Mermaid topology diagram, matched patterns, and 9+5 dimension analysis.
5. **Cross-app comparison**:
   ```bash
   harness compare <app1> <app2>
   ```

## Guardrails

- Respect `guard_status` in `reports/<app_name>.intermediate.json`: never present `unverified_capped` (1–2 star inferred) dimensions as confirmed architecture facts.
- Report any `blocked_sources` (Cloudflare/CAPTCHA/403/429) transparently; do not attempt to bypass anti-bot challenges.
