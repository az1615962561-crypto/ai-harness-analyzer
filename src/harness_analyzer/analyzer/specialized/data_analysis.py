"""数据分析类 AI 应用专属分析器"""
from .base import BaseSpecializedAnalyzer
from harness_analyzer.models.dimension import SpecializedDimension


class DataAnalyzer(BaseSpecializedAnalyzer):
    category = "data"

    def get_dimension_prompts(self) -> dict[str, tuple[str, str]]:
        return {
            SpecializedDimension.DATA_NL2SQL_PIPELINE.value: (
                SpecializedDimension.DATA_NL2SQL_PIPELINE.label,
                "分析 NL2SQL 管线：\n"
                "1) 自然语言理解与意图识别方式（规则/LLM/混合）？\n"
                "2) SQL 生成策略（直接生成/中间表示/多步骤）？\n"
                "3) 多轮对话中的查询细化与上下文继承？\n"
                "4) 复杂查询处理能力（JOIN/子查询/聚合/窗口函数）？\n"
                "5) SQL 正确性校验与自动修复机制？",
            ),
            SpecializedDimension.DATA_SOURCE_ADAPTER.value: (
                SpecializedDimension.DATA_SOURCE_ADAPTER.label,
                "分析数据源适配：\n"
                "1) 支持的数据源类型（关系型/NoSQL/数据湖/API/文件）？\n"
                "2) 连接池管理与连接复用策略？\n"
                "3) 多数据源联合查询能力？\n"
                "4) 数据源元数据自动发现与同步？\n"
                "5) 数据源权限与访问控制集成？",
            ),
            SpecializedDimension.DATA_SCHEMA_DISCOVERY.value: (
                SpecializedDimension.DATA_SCHEMA_DISCOVERY.label,
                "分析 Schema 发现：\n"
                "1) Schema 自动推断方式（数据库元数据/采样推断/用户标注）？\n"
                "2) 表关系自动发现（外键/命名约定/数据分析）？\n"
                "3) 字段语义理解与业务含义标注？\n"
                "4) Schema 变更检测与版本管理？\n"
                "5) 大规模 Schema（数百张表）的处理策略？",
            ),
            SpecializedDimension.DATA_QUERY_OPTIMIZATION.value: (
                SpecializedDimension.DATA_QUERY_OPTIMIZATION.label,
                "分析查询优化与安全：\n"
                "1) 查询执行计划优化（索引提示/查询改写）？\n"
                "2) 大数据量查询的分页与限制策略？\n"
                "3) SQL 注入防护与参数化查询？\n"
                "4) 查询超时控制与资源保护？\n"
                "5) 查询结果缓存与增量查询？",
            ),
            SpecializedDimension.DATA_VISUALIZATION_ENGINE.value: (
                SpecializedDimension.DATA_VISUALIZATION_ENGINE.label,
                "分析可视化引擎：\n"
                "1) 图表类型支持范围（基础图表/统计图/地理可视化/关系图）？\n"
                "2) 自动图表推荐与智能可视化选择？\n"
                "3) 交互式探索能力（钻取/筛选/联动）？\n"
                "4) 大数据量可视化性能优化（采样/聚合/流式渲染）？\n"
                "5) 可视化导出与报表生成能力？",
            ),
        }
