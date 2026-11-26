"""Shared dual-entrypoint pipeline for API-driven and Coding-Agent-native workflows."""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from harness_analyzer.analyzer.evidence import verify_all_dimensions
from harness_analyzer.analyzer.intermediate import IntermediateArtifactBuilder
from harness_analyzer.analyzer.patterns import load_pattern_catalog
from harness_analyzer.collectors.base import CollectedData
from harness_analyzer.collectors.blog import BlogCollector
from harness_analyzer.collectors.github import GitHubCollector
from harness_analyzer.collectors.query_planner import BilingualQueryPlanner
from harness_analyzer.collectors.reverse_eng import ReverseEngineeringCollector
from harness_analyzer.collectors.reviews import UserReviewCollector
from harness_analyzer.collectors.search import WebSearchCollector
from harness_analyzer.collectors.web_utils import DomainRateLimiter
from harness_analyzer.logging_utils import get_logger
from harness_analyzer.models.app import AIApp, AppCategory, InfoSource
from harness_analyzer.models.dimension import (
    CATEGORY_DIMENSIONS,
    CommonDimension,
    DIMENSION_WEIGHTS,
    DimensionAnalysis,
    SpecializedDimension,
    SpecializedDimensionAnalysis,
)
from harness_analyzer.models.harness import (
    BlockedSource,
    HarnessAnalysis,
    PMGuidance,
    SearchCoverageReport,
    UserReviewSummary,
)
from harness_analyzer.output.diagram import DiagramGenerator
from harness_analyzer.output.markdown import MarkdownReportGenerator
from harness_analyzer.registry.loader import AppRegistry
from harness_analyzer.storage.cache import AnalysisCache

logger = get_logger(__name__)

PRIMARY_SOURCE_TYPES = {
    "github_readme",
    "github_tree",
    "github_source",
    "blog",
    "blog_article",
    "docs",
    "documentation",
    "product_page",
    "re_repository",
    "github_re_search",
    "local_reverse_engineering",
}


class CollectedItemRecord(BaseModel):
    source_url: str
    source_type: str
    title: str
    content: str
    is_primary: bool = False


class CollectedBundle(BaseModel):
    """Portable evidence bundle produced by `harness collect` for Coding Agents or offline audit."""
    schema_version: str = "1.0"
    collected_at: datetime = Field(default_factory=datetime.now)
    app_name: str
    app_display_name: str
    category: str
    is_adhoc: bool = False
    description: str = ""
    website: str | None = None
    github_url: str | None = None
    question_lang: str = "zh"
    bilingual_names: dict[str, str] = Field(default_factory=dict)
    raw_sources: list[str] = Field(default_factory=list)
    search_coverage: SearchCoverageReport | None = None
    collected_items: list[CollectedItemRecord] = Field(default_factory=list)
    prompt_contract: dict[str, Any] = Field(default_factory=dict)


class DimensionDraftItem(BaseModel):
    dimension: str
    label: str = ""
    summary: str = ""
    details: str = ""
    key_decisions: list[str] = Field(default_factory=list)
    takeaways: list[str] = Field(default_factory=list)
    verbatim_quotes: list[str] = Field(default_factory=list)
    evidence_sources: list[str] = Field(default_factory=list)
    confidence: int = Field(default=3, ge=1, le=5)
    mermaid_diagram: str = ""


class AgentDraftInput(BaseModel):
    """Structured JSON draft produced by a Coding Agent reading CollectedBundle."""
    app_name: str | None = None
    app_display_name: str | None = None
    category: str | None = None
    architecture_summary: str = ""
    key_insights: list[str] = Field(default_factory=list)
    common_dimensions: list[DimensionDraftItem] = Field(default_factory=list)
    specialized_dimensions: list[DimensionDraftItem] = Field(default_factory=list)
    matched_patterns: list[dict[str, Any]] = Field(default_factory=list)
    user_reviews: UserReviewSummary | None = None
    pm_guidance: PMGuidance | None = None


def resolve_app_target(
    app_name: str,
    github: str | None = None,
    url: str | None = None,
) -> tuple[AIApp, bool]:
    """Resolve app from registry or synthesize an ad-hoc AIApp target."""
    registry = AppRegistry()
    app_obj = registry.get_app(app_name)
    is_adhoc = False
    if app_obj is None:
        is_adhoc = True
        app_obj = AIApp(
            name=app_name.lower().replace(" ", "-"),
            display_name=app_name,
            category=AppCategory.ENGINEERING,
            description=f"动态探测应用: {app_name}",
            github_url=github,
            website=url,
            info_richness=2,
        )
    else:
        if github:
            app_obj.github_url = github
        if url:
            app_obj.info_sources.append(InfoSource(url=url, source_type="blog", description="用户补充 URL"))
    return app_obj, is_adhoc


def category_info(category: Any) -> tuple[str, str]:
    cat_val = category.value if hasattr(category, "value") else str(category)
    cat_lbl = category.label if hasattr(category, "label") else cat_val
    return cat_val, cat_lbl


def build_prompt_contract(category: str = "engineering") -> dict[str, Any]:
    """Return exact dimension, weight, pattern, and output schema contract shared across entrypoints."""
    spec_by_cat = {
        cat: [{"dimension": d.value, "label": d.label} for d in dims]
        for cat, dims in CATEGORY_DIMENSIONS.items()
    }
    return {
        "categories": [c.value for c in AppCategory],
        "common_dimensions": [
            {
                "dimension": d.value,
                "label": d.label,
                "weight": DIMENSION_WEIGHTS.get(category, {}).get(d.value, 3),
            }
            for d in CommonDimension
        ],
        "specialized_dimensions_by_category": spec_by_cat,
        "pattern_catalog": load_pattern_catalog(),
        "guard_rules": {
            "core_requires_primary_verbatim_quote": True,
            "moderate_requires_any_verbatim_quote": True,
            "unverified_max_confidence": 2,
        },
        "expected_draft_schema": {
            "app_name": "string",
            "category": "engineering|data|knowledge|creative|automation",
            "architecture_summary": "string",
            "key_insights": ["string"],
            "common_dimensions": [
                {
                    "dimension": "agent_orchestration",
                    "summary": "string",
                    "details": "string",
                    "key_decisions": ["string"],
                    "takeaways": ["string"],
                    "verbatim_quotes": ["exact substring copied from collected_items"],
                    "evidence_sources": ["url or title"],
                    "confidence": 4,
                    "mermaid_diagram": "optional mermaid flowchart/sequence snippet (auto-generated if omitted)",
                }
            ],
            "specialized_dimensions": "same shape using 5 keys from specialized_dimensions_by_category[category]",
            "matched_patterns": [{"pattern_name": "string", "description": "string", "evidence": ["string"], "confidence": 4}],
            "user_reviews": {
                "review_sources": ["url"],
                "praises": ["string"],
                "pain_points": ["string"],
                "trust_and_ux_friction": ["string"],
                "sample_quotes": ["string"],
            },
            "pm_guidance": {
                "suitable_product_forms": ["string"],
                "autonomy_level": "L2 (...)",
                "interaction_design": "string",
                "cost_latency_tradeoffs": "string",
                "mvp_must_haves": ["string"],
                "mvp_nice_to_haves": ["string"],
                "anti_patterns_to_avoid": ["string"],
            },
        },
    }


async def collect_five_channels(
    app_obj: AIApp,
    lang: str = "zh",
    local_app: Path | None = None,
    use_rea: bool = False,
    llm: Any = None,
) -> tuple[list[CollectedData], SearchCoverageReport, dict[str, str], list[BlockedSource]]:
    """Run bilingual query planning, 5 concurrent collectors, refill, and circuit-breaker aggregation."""
    bilingual_names, planned_queries = BilingualQueryPlanner.plan_search_queries(
        app_obj.display_name, question_lang=lang, llm=llm
    )
    shared_limiter = DomainRateLimiter(min_interval=1.0, max_concurrency=4)
    searcher = WebSearchCollector(question_lang=lang, rate_limiter=shared_limiter)
    review_collector = UserReviewCollector(question_lang=lang)
    gh = GitHubCollector()
    blog = BlogCollector(rate_limiter=shared_limiter)
    re_collector = ReverseEngineeringCollector(local_app_path=local_app, use_rea=use_rea)

    results: list[CollectedData] = []
    refill_triggered = False

    gathered = await asyncio.gather(
        searcher.search_app(app_obj.display_name, planned_queries=planned_queries),
        gh.collect(app_obj),
        blog.collect(app_obj),
        re_collector.collect(app_obj),
        review_collector.collect(app_obj),
        return_exceptions=True,
    )
    for res in gathered:
        if isinstance(res, list):
            results.extend(res)
        elif isinstance(res, Exception):
            logger.warning("Collector channel raised exception for %s: %s", app_obj.name, res)

    cov_items = [*searcher.last_coverage_items, *review_collector.last_coverage_items]
    cov_report = BilingualQueryPlanner.build_coverage_report(
        cov_items, question_lang=lang, bilingual_names=bilingual_names
    )
    if cov_report.coverage_score < 0.6 or any(
        ang in cov_report.missing_angles for ang in ("architecture_qa", "user_reviews")
    ):
        refill_triggered = True
        existing_urls = {c.source_url for c in results if c.source_url}
        extra_data, extra_cov = await searcher.refill_missing_angles(
            app_obj.display_name, cov_report.missing_angles, existing_urls=existing_urls
        )
        results.extend(extra_data)
        cov_items.extend(extra_cov)

    blocked_all: list[BlockedSource] = list(shared_limiter.blocked_records)
    for item in [*searcher.last_blocked_sources, *gh.last_blocked_sources]:
        if isinstance(item, BlockedSource):
            blocked_all.append(item)
        elif isinstance(item, dict):
            blocked_all.append(BlockedSource(**item))

    search_coverage = BilingualQueryPlanner.build_coverage_report(
        cov_items,
        question_lang=lang,
        bilingual_names=bilingual_names,
        refill_triggered=refill_triggered,
        blocked_sources=blocked_all,
    )
    return results, search_coverage, bilingual_names, blocked_all


def build_collected_bundle(
    app_obj: AIApp,
    is_adhoc: bool,
    collected_items: list[CollectedData],
    search_coverage: SearchCoverageReport,
    bilingual_names: dict[str, str],
    lang: str = "zh",
) -> CollectedBundle:
    """Convert raw CollectedData list into a standalone CollectedBundle for Agent-native reasoning."""
    cat_val, _ = category_info(app_obj.category)
    raw_sources: list[str] = []
    records: list[CollectedItemRecord] = []
    for item in collected_items:
        if item.source_url and item.source_url not in raw_sources:
            raw_sources.append(item.source_url)
        records.append(
            CollectedItemRecord(
                source_url=item.source_url,
                source_type=item.source_type,
                title=item.title,
                content=item.content[:8000],
                is_primary=item.source_type in PRIMARY_SOURCE_TYPES,
            )
        )
    return CollectedBundle(
        app_name=app_obj.name,
        app_display_name=app_obj.display_name,
        category=cat_val,
        is_adhoc=is_adhoc,
        description=app_obj.description,
        website=app_obj.website,
        github_url=app_obj.github_url,
        question_lang=lang,
        bilingual_names=bilingual_names,
        raw_sources=raw_sources,
        search_coverage=search_coverage,
        collected_items=records,
        prompt_contract=build_prompt_contract(cat_val),
    )


def finalize_from_draft(bundle: CollectedBundle, draft: AgentDraftInput) -> HarnessAnalysis:
    """Verify a Coding Agent's analysis draft through Guard and synthesize full HarnessAnalysis."""
    raw_cat = (draft.category or bundle.category or "engineering").strip().lower()
    cat_val = raw_cat if any(c.value == raw_cat for c in AppCategory) else "engineering"
    try:
        cat_lbl = AppCategory(cat_val).label
    except ValueError:
        cat_lbl = cat_val

    common_labels = {d.value: d.label for d in CommonDimension}
    spec_labels = {d.value: d.label for d in SpecializedDimension}

    common_dims = [
        DimensionAnalysis(
            dimension=d.dimension,
            label=d.label or common_labels.get(d.dimension, d.dimension),
            summary=d.summary or "暂无总结",
            details=d.details,
            key_decisions=d.key_decisions,
            takeaways=d.takeaways,
            verbatim_quotes=d.verbatim_quotes,
            evidence_sources=d.evidence_sources,
            confidence=d.confidence,
            mermaid_diagram=d.mermaid_diagram,
        )
        for d in draft.common_dimensions
    ]
    spec_dims = [
        SpecializedDimensionAnalysis(
            dimension=d.dimension,
            label=d.label or spec_labels.get(d.dimension, d.dimension),
            summary=d.summary or "暂无总结",
            details=d.details,
            key_decisions=d.key_decisions,
            takeaways=d.takeaways,
            verbatim_quotes=d.verbatim_quotes,
            evidence_sources=d.evidence_sources,
            confidence=d.confidence,
            mermaid_diagram=d.mermaid_diagram,
        )
        for d in draft.specialized_dimensions
    ]

    raw_corpus_parts = [it.content for it in bundle.collected_items]
    primary_corpus_parts = [
        it.content for it in bundle.collected_items
        if it.is_primary or it.source_type in PRIMARY_SOURCE_TYPES
    ]
    review_items = [
        CollectedData(source_url=it.source_url, source_type=it.source_type, title=it.title, content=it.content)
        for it in bundle.collected_items
        if it.source_type == "user_review"
    ]

    common_dims, spec_dims = verify_all_dimensions(
        common_dims,
        spec_dims,
        "\n\n".join(raw_corpus_parts),
        category=cat_val,
        primary_corpus="\n\n".join(primary_corpus_parts),
    )

    app_name = draft.app_name or bundle.app_name
    display_name = draft.app_display_name or bundle.app_display_name

    intermediate_artifact = IntermediateArtifactBuilder(llm=None).build(
        app_name=app_name,
        category=cat_val,
        common_dims=common_dims,
        specialized_dims=spec_dims,
        review_items=review_items,
        user_reviews_override=draft.user_reviews,
        search_coverage=bundle.search_coverage,
    )

    pm_guidance = draft.pm_guidance
    if pm_guidance is None:
        from harness_analyzer.analyzer.pm_guidance import PMGuidanceExtractor
        pm_guidance = PMGuidanceExtractor._fallback_guidance(cat_val)

    all_dims = [*common_dims, *spec_dims]
    confidence_overall = (
        round(sum(d.confidence for d in all_dims) / len(all_dims))
        if all_dims
        else 2
    )

    analysis = HarnessAnalysis(
        app_name=app_name,
        app_display_name=display_name,
        category=cat_val,
        intermediate_artifact=intermediate_artifact,
        pm_guidance=pm_guidance,
        common_dimensions=common_dims,
        specialized_dimensions=spec_dims,
        matched_patterns=draft.matched_patterns,
        architecture_summary=draft.architecture_summary or f"{display_name} 是一个{cat_lbl}类 AI 应用",
        key_insights=draft.key_insights or [d.summary for d in common_dims if d.confidence >= 3][:5],
        raw_sources=bundle.raw_sources,
        source_count=len(bundle.collected_items),
        confidence_overall=max(1, min(5, confidence_overall)),
    )
    analysis.mermaid_diagram = DiagramGenerator().generate(analysis)
    return analysis


def persist_analysis_artifacts(
    analysis: HarnessAnalysis,
    cache_dir: Path,
    reports_dir: Path,
) -> tuple[Path, Path | None]:
    """Save analysis to SQLite cache, write .intermediate.json and 3-layer .md report."""
    cat_val = analysis.category.value if hasattr(analysis.category, "value") else str(analysis.category)
    cache = AnalysisCache(cache_dir)
    cache.save(analysis.app_name, cat_val, analysis.model_dump_json())

    intermediate_path = None
    if analysis.intermediate_artifact is not None:
        intermediate_path = IntermediateArtifactBuilder.save_to_disk(
            analysis.intermediate_artifact, reports_dir, analysis.app_name
        )

    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{analysis.app_name}.md"
    report_path.write_text(MarkdownReportGenerator().generate(analysis), encoding="utf-8")
    return report_path, intermediate_path
