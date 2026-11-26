"""应用层：产品经理方案指导生成器 (PM Guidance Extractor)
直接以第二步→第三步产出的结构化中间产物 (IntermediateArtifact) 为依据，
结合已验证的技术事实与权威真实用户评论痛点，转化为产品经理可直接落地的 PRD 方案指导。
"""
from __future__ import annotations

from harness_analyzer.models.dimension import DimensionAnalysis, SpecializedDimensionAnalysis
from harness_analyzer.models.harness import IntermediateArtifact, PMGuidance
from harness_analyzer.logging_utils import get_logger
from .intermediate import IntermediateArtifactBuilder
from .llm import LLMClient

logger = get_logger(__name__)


class PMGuidanceExtractor:
    """基于中间产物与真实用户评论，生成产品经理视角的落地指导方案"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_from_artifact(self, app_info: str, artifact: IntermediateArtifact) -> PMGuidance:
        """直接消费 IntermediateArtifact 进行应用层产品方案转化"""
        core_block = "\n".join(f"- {x}" for x in artifact.core_verified_facts) or "- 暂无严格实证的核心事实"
        mod_block = "\n".join(f"- {x}" for x in artifact.moderate_findings) or "- 暂无"
        warn_block = "\n".join(f"- {x}" for x in artifact.inferred_warnings) or "- 无"

        reviews_block = "暂无社区用户评论数据。"
        if artifact.user_reviews:
            ur = artifact.user_reviews
            praises = "\n".join(f"  + {p}" for p in ur.praises) or "  + 暂无"
            pains = "\n".join(f"  - {p}" for p in ur.pain_points) or "  - 暂无"
            frictions = "\n".join(f"  ! {f}" for f in ur.trust_and_ux_friction) or "  ! 暂无"
            reviews_block = (
                f"用户正面爽点：\n{praises}\n"
                f"用户高频痛点：\n{pains}\n"
                f"人机信任与交互摩擦：\n{frictions}"
            )

        coverage_block = "离线基准知识库模式（未执行在线搜索统计）。"
        if artifact.search_coverage:
            sc = artifact.search_coverage
            coverage_block = (
                f"覆盖度得分：{sc.coverage_score:.0%} "
                f"(中文命中 {sc.zh_hits} 条 / 英文命中 {sc.en_hits} 条)\n"
                f"已覆盖角度：{', '.join(sc.covered_angles) or '无'}\n"
                f"覆盖盲区：{', '.join(sc.missing_angles) or '无'}"
            )

        system_prompt = (
            "你是一位既懂 AI 底层 Harness 工程又精通商业产品落地的资深 AI 产品总监。"
            "请严格依据提供的【中间产物（已分维度 Guard 校验）】、【检索覆盖度评估】与【真实用户评论洞察】，"
            "输出产品经理可直接写入 PRD 的方案指导。"
            "注意：对于标记在『未实证推断警示』或处于『覆盖盲区』的能力，切勿盲目列为 P0 硬性照搬项。"
        )

        prompt = (
            f"## 目标对标应用信息\n{app_info}\n\n"
            f"## 所属品类：{artifact.category}\n\n"
            f"## 中间产物 1：核心强关联且已严格实证的架构事实 (P0 转化主依据)\n{core_block}\n\n"
            f"## 中间产物 2：中度/弱关联维度发现\n{mod_block}\n\n"
            f"## 中间产物 3：未通过实证 Guard 的推断警示 (PM 谨慎引用)\n{warn_block}\n\n"
            f"## 中间产物 4：双语检索内容覆盖度评估\n{coverage_block}\n\n"
            f"## 中间产物 5：权威社区真实用户评论与痛点\n{reviews_block}\n\n"
            "## 任务\n"
            "综合以上中间产物与用户真实痛点，从产品经理视角给出落地指导，严格返回以下 JSON 结构：\n"
            "{\n"
            '  "suitable_product_forms": ["最适合的产品形态1", "形态2"],\n'
            '  "autonomy_level": "L1~L4 自主度评级及一句话定位",\n'
            '  "interaction_design": "人机协同与用户信任建立机制设计（重点针对上述用户痛点与信任摩擦给出解法）",\n'
            '  "cost_latency_tradeoffs": "响应延迟与 Token 成本的体验权衡策略",\n'
            '  "mvp_must_haves": ["第一期 P0 必须功能1", "功能2", "功能3"],\n'
            '  "mvp_nice_to_haves": ["第二期 P1 增强功能1", "功能2"],\n'
            '  "anti_patterns_to_avoid": ["结合用户吐槽和未实证风险提炼的产品避坑红线1", "红线2"]\n'
            "}"
        )

        try:
            data = self.llm.structured_analyze(prompt, system_prompt)
            return PMGuidance(
                suitable_product_forms=data.get("suitable_product_forms", []) or [],
                autonomy_level=data.get("autonomy_level", "L2 (协同辅助型)"),
                interaction_design=data.get("interaction_design", ""),
                cost_latency_tradeoffs=data.get("cost_latency_tradeoffs", ""),
                mvp_must_haves=data.get("mvp_must_haves", []) or [],
                mvp_nice_to_haves=data.get("mvp_nice_to_haves", []) or [],
                anti_patterns_to_avoid=data.get("anti_patterns_to_avoid", []) or [],
            )
        except Exception as exc:
            logger.warning("PM guidance extraction fallback used for %s: %s", artifact.app_name, exc)
            return self._fallback_guidance(artifact.category)

    def extract(
        self,
        app_info: str,
        category: str,
        common_dims: list[DimensionAnalysis],
        specialized_dims: list[SpecializedDimensionAnalysis],
    ) -> PMGuidance:
        """向后兼容的便捷入口：内部先合成 IntermediateArtifact 再转化 PM 方案"""
        artifact = IntermediateArtifactBuilder().build(
            app_name="target",
            category=category,
            common_dims=common_dims,
            specialized_dims=specialized_dims,
        )
        return self.extract_from_artifact(app_info, artifact)

    @staticmethod
    def _fallback_guidance(category: str) -> PMGuidance:
        """LLM 解析失败时的分类兜底建议"""
        return PMGuidance(
            suitable_product_forms=[f"面向 {category} 场景的嵌入式协同工作台或对话助手"],
            autonomy_level="L2 (人在回路协同型)",
            interaction_design="为关键操作提供前置预览、结构化确认和一键撤销机制，降低用户心理门槛。",
            cost_latency_tradeoffs="高频轻量任务路由至高速小模型，复杂推理异步流式返回以兼顾体验与成本。",
            mvp_must_haves=["核心业务流程端到端闭环", "结果前置确认与错误处理", "用户反馈收集入口"],
            mvp_nice_to_haves=["多模型分级路由降本", "历史版本快照回滚"],
            anti_patterns_to_avoid=["首期切忌盲目追求全自动黑盒托管", "避免未做上下文剪枝直接全量塞入大模型"],
        )
