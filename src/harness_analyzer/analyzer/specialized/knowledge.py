"""知识管理类 AI 应用专属分析器"""
from .base import BaseSpecializedAnalyzer
from harness_analyzer.models.dimension import SpecializedDimension


class KnowledgeAnalyzer(BaseSpecializedAnalyzer):
    category = "knowledge"

    def get_dimension_prompts(self) -> dict[str, tuple[str, str]]:
        return {
            SpecializedDimension.KNOW_RAG_PIPELINE.value: (
                SpecializedDimension.KNOW_RAG_PIPELINE.label,
                "分析 RAG 检索管线：\n"
                "1) 文档切分策略（固定长度/语义段落/递归分割/AST 感知）？\n"
                "2) 嵌入模型选型与向量维度？\n"
                "3) 检索策略（稠密检索/稀疏检索/混合检索/重排序）？\n"
                "4) 检索结果的相关性过滤与去重？\n"
                "5) 多路召回与融合排序机制？",
            ),
            SpecializedDimension.KNOW_INDEX_VECTOR_STORE.value: (
                SpecializedDimension.KNOW_INDEX_VECTOR_STORE.label,
                "分析知识索引与向量存储：\n"
                "1) 文档解析支持（PDF/Word/HTML/Markdown/代码）？\n"
                "2) 数据源连接器架构（网页/文件/数据库/SaaS 权限过滤）？\n"
                "3) 索引存储方案（向量数据库选型/混合索引分片）？\n"
                "4) 多租户索引隔离与访问控制？\n"
                "5) 索引质量监控与检索延迟优化？",
            ),
            SpecializedDimension.KNOW_CITATION_MANAGEMENT.value: (
                SpecializedDimension.KNOW_CITATION_MANAGEMENT.label,
                "分析引用链管理与溯源：\n"
                "1) 引用生成方式（句子级角标/精确段落引用/页码定位/URL 快照）？\n"
                "2) 事实性校验机制（交叉验证/实体对齐/知识图谱核查）？\n"
                "3) 幻觉检测与忠实度自评策略？\n"
                "4) 引用失配防护与前端悬停溯源交互？\n"
                "5) 无引用或弱证据场景的降级提示？",
            ),
            SpecializedDimension.KNOW_MULTI_DOC_REASONING.value: (
                SpecializedDimension.KNOW_MULTI_DOC_REASONING.label,
                "分析多文档综合推理：\n"
                "1) 答案合成策略（抽取式/生成式/Map-Reduce 多段归纳）？\n"
                "2) 多文档信息融合与正反立场冲突消解？\n"
                "3) 跨文档实体链接与时间轴对齐？\n"
                "4) 答案质量自评与引导式延伸追问？\n"
                "5) 长文档集的分段摘要与证据聚合？",
            ),
            SpecializedDimension.KNOW_KNOWLEDGE_UPDATE.value: (
                SpecializedDimension.KNOW_KNOWLEDGE_UPDATE.label,
                "分析知识动态更新机制：\n"
                "1) 增量索引与实时变更捕捉（Webhook/CDC/定时重爬）？\n"
                "2) 知识时效性衰减加权与过期事实淘汰？\n"
                "3) 文档版本管理与删除/撤回同步？\n"
                "4) 高频变化知识与静态沉淀知识的冷热分层？\n"
                "5) 更新冲突处理与一致性保障？",
            ),
        }
