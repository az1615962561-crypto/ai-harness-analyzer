"""创意类 AI 应用专属分析器"""
from .base import BaseSpecializedAnalyzer
from harness_analyzer.models.dimension import SpecializedDimension


class CreativeAnalyzer(BaseSpecializedAnalyzer):
    category = "creative"

    def get_dimension_prompts(self) -> dict[str, tuple[str, str]]:
        return {
            SpecializedDimension.CREA_MULTIMODAL_PIPELINE.value: (
                SpecializedDimension.CREA_MULTIMODAL_PIPELINE.label,
                "分析多模态生成管线：\n"
                "1) 生成流程架构（单步生成/多步迭代/多模态级联协调）？\n"
                "2) 生成模型选型（文本 LLM/图像扩散模型/音视频模型路由）？\n"
                "3) 跨模态对齐、条件控制与约束注入机制？\n"
                "4) 生成结果质量过滤与安全审核？\n"
                "5) 异步渲染调度与成本控制？",
            ),
            SpecializedDimension.CREA_VERSION_VARIANT.value: (
                SpecializedDimension.CREA_VERSION_VARIANT.label,
                "分析版本与变体管理：\n"
                "1) 多候选变体并发生成与对比选择机制？\n"
                "2) 局部重绘/局部改写（Inpainting / Selective Edit）与迭代收敛策略？\n"
                "3) 历史版本树、Seed 复现与回滚对比能力？\n"
                "4) 用户自然语言反馈到精细参数修改的映射？\n"
                "5) 导出多尺寸/多格式变体工作流？",
            ),
            SpecializedDimension.CREA_REALTIME_PREVIEW.value: (
                SpecializedDimension.CREA_REALTIME_PREVIEW.label,
                "分析实时渲染与预览：\n"
                "1) 流式预览架构（草稿帧/低步数扩散预览/代码沙箱热重载）？\n"
                "2) 交互式画布或分屏同步编辑延迟？\n"
                "3) 增量局部渲染而非全量重算优化？\n"
                "4) 客户端渲染 vs 云端 GPU 推送策略？\n"
                "5) 加载反馈与可打断生成体验？",
            ),
            SpecializedDimension.CREA_STYLE_CONSISTENCY.value: (
                SpecializedDimension.CREA_STYLE_CONSISTENCY.label,
                "分析风格一致性控制：\n"
                "1) 风格定义方式（参考图/LoRA/示例/Design Token/文字规范）？\n"
                "2) 跨页面/跨帧/跨章节角色与视觉调性一致性保障？\n"
                "3) 风格迁移与多风格混合控制？\n"
                "4) 品牌调性与企业视觉规范强制约束？\n"
                "5) 用户偏好风格的沉淀与复用？",
            ),
            SpecializedDimension.CREA_TEMPLATE_REUSE.value: (
                SpecializedDimension.CREA_TEMPLATE_REUSE.label,
                "分析模板与资产复用：\n"
                "1) 模板体系设计（组件化/层级继承/约束插槽）？\n"
                "2) 资产库管理（上传/语义检索/标签/版本控制）？\n"
                "3) 模板参数化与动态内容填充能力？\n"
                "4) 智能版式匹配与素材自动推荐？\n"
                "5) 企业素材权限、合规与版权水印追踪？",
            ),
        }
