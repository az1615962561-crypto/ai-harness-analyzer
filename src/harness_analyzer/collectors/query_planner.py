"""双语多维度检索规划与覆盖度评估器 (Bilingual Query Planner & Coverage Evaluator)
根据用户提问语言 + 英语执行双重检索：
- 提问语言（如中文）：如「claude的架构是什么」、「claude 底层原理 工具调用 拆解」、「claude 真实体验 吐槽」
- 英语（全球一手技术信源）：如「how the claude works architecture」、「claude system prompt tools harness」、「claude review pros cons」
并评估每个角度与语种的内容覆盖度，防止单一检索词盲区导致分析失真。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from harness_analyzer.models.harness import BlockedSource, QueryCoverageItem, SearchCoverageReport


@dataclass(frozen=True)
class PlannedQuery:
    """单条规划检索词及其语义维度标签"""
    query: str
    language: str  # "zh" / "en"
    angle: str     # "architecture_qa" / "implementation_tech" / "source_reverse" / "user_reviews"


# 常见中外 AI 应用双语名称映射表（无 LLM 情况下也能零延迟映射）
_BILINGUAL_ALIASES: dict[str, tuple[str, str]] = {
    "扣子": ("扣子", "Coze"),
    "coze": ("扣子 Coze", "Coze"),
    "通义千问": ("通义千问", "Qwen"),
    "qwen": ("通义千问", "Qwen"),
    "秘塔": ("秘塔AI搜索", "Metaso"),
    "metaso": ("秘塔AI搜索", "Metaso"),
    "豆包": ("豆包", "Doubao"),
    "doubao": ("豆包", "Doubao"),
    "kimi": ("Kimi", "Kimi Moonshot"),
    "智谱清言": ("智谱清言", "Zhipu GLM"),
    "claude": ("Claude", "Claude"),
    "claude-code": ("Claude Code", "Claude Code"),
    "cursor": ("Cursor", "Cursor"),
    "devin": ("Devin", "Devin"),
    "perplexity": ("Perplexity", "Perplexity"),
    "chatbi": ("ChatBI", "ChatBI"),
    "manus": ("Manus", "Manus AI"),
    "manus-ai": ("Manus", "Manus AI"),
    "autogpt": ("AutoGPT", "AutoGPT"),
}

_ALL_ANGLES = ("architecture_qa", "implementation_tech", "source_reverse", "user_reviews")


class BilingualQueryPlanner:
    """生成「提问语言 + 英语」双语检索矩阵并计算内容覆盖度"""

    @staticmethod
    def detect_language(text: str) -> str:
        """粗略判断输入文本属于中文还是英文"""
        if re.search(r"[\u4e00-\u9fff]", text or ""):
            return "zh"
        return "en"

    @classmethod
    def resolve_bilingual_names(
        cls,
        app_name: str,
        question_lang: str = "zh",
        llm: Any = None,
    ) -> dict[str, str]:
        """解析应用在提问语言与英语中的检索名，返回 {'local': ..., 'en': ...}"""
        norm = app_name.strip().lower()
        if norm in _BILINGUAL_ALIASES:
            local_name, en_name = _BILINGUAL_ALIASES[norm]
            return {"local": local_name, "en": en_name}

        has_cjk = bool(re.search(r"[\u4e00-\u9fff]", app_name))
        if has_cjk and llm is not None:
            try:
                en_guess = llm.analyze(
                    f"请给出 AI 产品 '{app_name}' 最常用的官方英文名称或拼音名（仅输出英文名称，不要解释）："
                ).strip().splitlines()[0]
                en_clean = re.sub(r"[^a-zA-Z0-9 ._-]", "", en_guess).strip()
                if en_clean:
                    return {"local": app_name.strip(), "en": en_clean}
            except Exception:
                pass

        return {"local": app_name.strip(), "en": app_name.strip()}

    @classmethod
    def plan_search_queries(
        cls,
        app_name: str,
        question_lang: str = "zh",
        llm: Any = None,
    ) -> tuple[dict[str, str], list[PlannedQuery]]:
        """生成面向技术架构、实现细节与逆向信源的双语检索词列表"""
        names = cls.resolve_bilingual_names(app_name, question_lang=question_lang, llm=llm)
        local_name = names["local"]
        en_name = names["en"]

        queries: list[PlannedQuery] = []

        # 1. 英语核心技术检索（覆盖全球一手工程博客、英文提问式深文与开源代码）
        queries.extend([
            PlannedQuery(
                query=f"how the {en_name} works AI architecture",
                language="en",
                angle="architecture_qa",
            ),
            PlannedQuery(
                query=f"{en_name} AI engineering blog system architecture",
                language="en",
                angle="architecture_qa",
            ),
            PlannedQuery(
                query=f"{en_name} system prompt tools agent harness",
                language="en",
                angle="implementation_tech",
            ),
            PlannedQuery(
                query=f"{en_name} AI agent github reverse engineering",
                language="en",
                angle="source_reverse",
            ),
        ])

        # 2. 提问语言检索（当用户以中文提问时，补充自然语言提问式 + 中文工程拆解词）
        if question_lang == "zh":
            queries.extend([
                PlannedQuery(
                    query=f"{local_name}的架构是什么",
                    language="zh",
                    angle="architecture_qa",
                ),
                PlannedQuery(
                    query=f"{local_name} AI 底层原理 技术架构 拆解",
                    language="zh",
                    angle="architecture_qa",
                ),
                PlannedQuery(
                    query=f"{local_name} 提示词 工具调用 Agent 工作流",
                    language="zh",
                    angle="implementation_tech",
                ),
                PlannedQuery(
                    query=f"{local_name} 开源 源码 逆向",
                    language="zh",
                    angle="source_reverse",
                ),
            ])

        return names, queries

    @classmethod
    def plan_review_queries(
        cls,
        app_name: str,
        question_lang: str = "zh",
        llm: Any = None,
    ) -> list[PlannedQuery]:
        """生成双语权威用户评论检索词列表"""
        names = cls.resolve_bilingual_names(app_name, question_lang=question_lang, llm=llm)
        local_name = names["local"]
        en_name = names["en"]

        queries = [
            PlannedQuery(
                query=f'"{en_name}" (site:g2.com OR site:producthunt.com OR site:trustpilot.com) review',
                language="en",
                angle="user_reviews",
            ),
            PlannedQuery(
                query=f'"{en_name}" ("pros and cons" OR "frustrating" OR "review" OR "issues") site:reddit.com',
                language="en",
                angle="user_reviews",
            ),
        ]
        if question_lang == "zh":
            queries.append(
                PlannedQuery(
                    query=f'"{local_name}" (真实体验 OR 缺点 OR 吐槽 OR 评测) (site:zhihu.com OR site:v2ex.com OR site:juejin.cn)',
                    language="zh",
                    angle="user_reviews",
                )
            )
        return queries

    @classmethod
    def plan_refill_queries(
        cls,
        app_name: str,
        missing_angles: list[str],
        question_lang: str = "zh",
        llm: Any = None,
    ) -> list[PlannedQuery]:
        """针对覆盖度不足或命中的盲区角度，生成更宽泛的二次补搜关键词"""
        names = cls.resolve_bilingual_names(app_name, question_lang=question_lang, llm=llm)
        local_name = names["local"]
        en_name = names["en"]
        refills: list[PlannedQuery] = []

        if "architecture_qa" in missing_angles:
            refills.append(PlannedQuery(query=f"{en_name} AI explained", language="en", angle="architecture_qa"))
            if question_lang == "zh":
                refills.append(PlannedQuery(query=f"{local_name} AI 原理", language="zh", angle="architecture_qa"))
        if "implementation_tech" in missing_angles:
            refills.append(PlannedQuery(query=f"{en_name} LLM tools workflow", language="en", angle="implementation_tech"))
        if "source_reverse" in missing_angles:
            refills.append(PlannedQuery(query=f"{en_name} github", language="en", angle="source_reverse"))
        if "user_reviews" in missing_angles:
            refills.append(PlannedQuery(query=f"{en_name} review feedback", language="en", angle="user_reviews"))
            if question_lang == "zh":
                refills.append(PlannedQuery(query=f"{local_name} 好用吗 评测", language="zh", angle="user_reviews"))

        return refills

    @staticmethod
    def build_coverage_report(
        items: list[QueryCoverageItem],
        question_lang: str = "zh",
        bilingual_names: dict[str, str] | None = None,
        refill_triggered: bool = False,
        blocked_sources: list[BlockedSource] | None = None,
    ) -> SearchCoverageReport:
        """汇总各搜索词的命中与正文提取情况，评估信息覆盖度与盲区"""
        zh_hits = sum(i.hits_count for i in items if i.language == "zh")
        en_hits = sum(i.hits_count for i in items if i.language == "en")

        angle_hits: dict[str, int] = {a: 0 for a in _ALL_ANGLES}
        for i in items:
            if i.angle in angle_hits:
                angle_hits[i.angle] += i.hits_count

        covered_angles = [a for a, cnt in angle_hits.items() if cnt > 0]
        missing_angles = [a for a, cnt in angle_hits.items() if cnt == 0]

        angle_ratio = len(covered_angles) / len(_ALL_ANGLES)
        if question_lang == "zh":
            lang_bonus = (0.15 if zh_hits > 0 else 0.0) + (0.15 if en_hits > 0 else 0.0)
        else:
            lang_bonus = 0.30 if en_hits > 0 else 0.0

        score = round(min(1.0, angle_ratio * 0.7 + lang_bonus), 2)

        return SearchCoverageReport(
            question_language=question_lang,
            bilingual_names=bilingual_names or {},
            items=items,
            zh_hits=zh_hits,
            en_hits=en_hits,
            covered_angles=covered_angles,
            missing_angles=missing_angles,
            coverage_score=score,
            refill_triggered=refill_triggered,
            blocked_sources=blocked_sources or [],
        )
