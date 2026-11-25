"""Tests for LLM client, CommonDimensionExtractor, and PMGuidanceExtractor."""
from unittest.mock import MagicMock
from harness_analyzer.analyzer.llm import LLMClient
from harness_analyzer.analyzer.dimensions import CommonDimensionExtractor, DIMENSION_PROMPTS
from harness_analyzer.analyzer.pm_guidance import PMGuidanceExtractor
from harness_analyzer.models.dimension import CommonDimension, DimensionAnalysis, SpecializedDimensionAnalysis


def test_llm_extract_json_variants():
    assert LLMClient.extract_json('{"a": 1}') == {"a": 1}
    assert LLMClient.extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert LLMClient.extract_json('以下是分析结果：\n```json\n{"summary": "ok"}\n```\n完成。') == {"summary": "ok"}
    assert LLMClient.extract_json('Result: [{"pattern_name": "RAG"}]') == [{"pattern_name": "RAG"}]


def test_dimension_prompts_align_with_common_dimension_enum():
    for dim in CommonDimension:
        assert dim.value in DIMENSION_PROMPTS, f"Missing prompt for {dim.value}"


def test_common_dimension_extractor_respects_category_weights_and_depth():
    mock_llm = MagicMock()
    mock_llm.structured_analyze.return_value = {
        "summary": "Core summary",
        "details": "Detailed explanation",
        "key_decisions": ["Decision A"],
        "takeaways": ["Takeaway A"],
        "evidence_sources": ["Source A"],
        "confidence": 4,
    }
    extractor = CommonDimensionExtractor(mock_llm)

    # For 'data' category in 'quick' depth, dims with weight < 3 (agent_orchestration=2, extensibility_ecosystem=2) are skipped
    quick_results = extractor.extract_all("ChatBI", "data", category="data", depth="quick")
    quick_dims = {r.dimension for r in quick_results}
    assert "agent_orchestration" not in quick_dims
    assert "extensibility_ecosystem" not in quick_dims
    assert "prompt_engineering" in quick_dims
    assert all(isinstance(r, DimensionAnalysis) and r.label for r in quick_results)

    # For 'engineering' category in 'full' depth, all 9 dimensions have weight >= 4
    full_results = extractor.extract_all("Cursor", "data", category="engineering", depth="full")
    assert len(full_results) == 9

    # Filtering by specific dimensions
    filtered = extractor.extract_all("Cursor", "data", category="engineering", only_dimensions=["model_routing"])
    assert len(filtered) == 1
    assert filtered[0].dimension == "model_routing"
    assert filtered[0].label == "模型路由"


def test_pm_guidance_extractor_and_fallback():
    mock_llm = MagicMock()
    mock_llm.structured_analyze.return_value = {
        "suitable_product_forms": ["Web 工作台"],
        "autonomy_level": "L2",
        "interaction_design": "Diff preview",
        "cost_latency_tradeoffs": "Route small models",
        "mvp_must_haves": ["Feature 1"],
        "mvp_nice_to_haves": ["Feature 2"],
        "anti_patterns_to_avoid": ["No blackbox"],
    }
    extractor = PMGuidanceExtractor(mock_llm)
    pm = extractor.extract(
        "Cursor",
        "engineering",
        [DimensionAnalysis(dimension="model_routing", label="模型路由", summary="Routing")],
        [SpecializedDimensionAnalysis(dimension="sandbox_model", label="沙箱", summary="Local")],
    )
    assert pm.suitable_product_forms == ["Web 工作台"]
    assert pm.mvp_must_haves == ["Feature 1"]

    # Fallback on error
    mock_llm.structured_analyze.side_effect = RuntimeError("JSON fail")
    fallback_pm = extractor.extract("Cursor", "engineering", [], [])
    assert len(fallback_pm.suitable_product_forms) > 0
    assert len(fallback_pm.mvp_must_haves) > 0
