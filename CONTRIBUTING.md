# Contributing to AI Harness Analyzer

Thank you for helping improve `ai-harness-analyzer`!

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verify your environment with:

```bash
harness doctor
pytest -v tests/
```

## Project Layout

- `src/harness_analyzer/models/` — Pydantic schemas (`AIApp`, `DimensionAnalysis`, `SpecializedDimension`, `HarnessAnalysis`, `IntermediateArtifact`, `PMGuidance`)
- `src/harness_analyzer/registry/apps.yaml` — Built-in AI application registry (5 categories)
- `src/harness_analyzer/collectors/` — Five-channel collectors (Web Search, GitHub, Blog, Reviews, Reverse Engineering) with anti-bot circuit breakers
- `src/harness_analyzer/analyzer/` — Two-stage FactSheet extraction, concurrent 9+5 dimensions, `PatternMatcher`, coupling-tiered `Guard`, `IntermediateArtifactBuilder`, and `PMGuidanceExtractor`
- `src/harness_analyzer/output/` — PM-first Markdown report, comparison matrix, and Mermaid diagrams
- `data/patterns/*.yaml` — Reference architecture pattern catalog loaded by `PatternMatcher`
- `data/prompts/*.md` — Standalone prompt templates for manual inspection/reference

## Adding a New App to the Registry

1. Edit `src/harness_analyzer/registry/apps.yaml` following existing schema (`name`, `display_name`, `category`, `tags`, `website`, `github_url`, `info_richness`, `info_sources`).
2. Run `harness info <app_name>` to verify loading and `pytest -v tests/` to ensure schema integrity.

## Environment Variables

- `GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — Required for online LLM analysis
- `HARNESS_LLM_PROVIDER`, `HARNESS_LLM_MODEL` — Model routing override
- `HARNESS_MAX_CONCURRENCY` (default `5`), `HARNESS_LLM_MAX_RETRIES` (default `3`) — Concurrency & retry tuning
- `HARNESS_CACHE_DIR` (default `.cache`), `HARNESS_REPORTS_DIR` (default `reports`) — Output directories
- `TAVILY_API_KEY`, `GITHUB_TOKEN` — Optional fast search & higher GitHub API quota

## Testing & Code Style

- **Dual-Entrypoint Sync Rule**: This project maintains two first-class entrypoints — **CLI API Mode** (`harness analyze`) and **Coding-Agent Native Mode** (`harness collect` -> Agent draft -> `harness finalize`) — backed by `src/harness_analyzer/pipeline.py`. Keep both entrypoints synchronized whenever changing collectors, dimension schemas, Guard verification, caches, or report generation.
- Keep existing comments/docstrings intact and avoid network calls in unit tests (use `unittest.mock` / `httpx.MockTransport`).
- Always run `pytest -v tests/` before opening a PR.
