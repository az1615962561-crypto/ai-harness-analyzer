"""多应用架构对比报告生成器"""
from datetime import datetime
from typing import Any


class ComparisonReportGenerator:
    """生成多个 AI 应用 Harness 架构的横向对比 Markdown 报告"""

    @staticmethod
    def _format_stars(conf: Any) -> str:
        """将置信度格式化为星级字符串"""
        if conf is None:
            return "★★★☆☆"
        if isinstance(conf, (int, float)):
            if 0 < conf <= 1.0:
                stars = round(conf * 5)
            else:
                stars = round(conf)
            stars = max(1, min(5, stars))
            return "★" * stars + "☆" * (5 - stars)
        return str(conf)

    @staticmethod
    def _get_val(obj: Any, *keys: str, default: Any = "") -> Any:
        """从对象或字典中提取字段"""
        for k in keys:
            if isinstance(obj, dict) and k in obj and obj[k] is not None:
                return obj[k]
            if hasattr(obj, k) and getattr(obj, k) is not None:
                return getattr(obj, k)
        return default

    def generate(self, analyses: list[Any]) -> str:
        """生成多个应用架构的横向对比 Markdown 报告"""
        if not analyses:
            return "# AI Harness 架构横向对比分析报告\n\n暂无对比数据。"

        app_names = [
            str(self._get_val(a, "app_display_name", "app_name", default=f"应用 {i+1}"))
            for i, a in enumerate(analyses)
        ]

        sections = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. 标题
        title = f"# AI Harness 架构对比报告：{' vs '.join(app_names)}\n"
        sections.append(title)
        sections.append(f"> 生成时间：{now_str} | 对比数量：{len(analyses)} 款 AI 应用\n")

        # 2. 概览对比表
        sections.append("## 1. 概览横向对比\n")
        table_headers = ["对比维度"] + app_names
        table_sep = [":---"] + [":---"] * len(app_names)

        categories = []
        for a in analyses:
            cat = self._get_val(a, "category", default="通用")
            if hasattr(cat, "value"):
                cat = cat.value
            categories.append(str(cat))

        overview_rows = [
            ["**应用分类**"] + categories,
            ["**架构置信度**"] + [self._format_stars(self._get_val(a, "confidence", default=None)) for a in analyses],
            ["**信息源数量**"] + [
                str(self._get_val(a, "source_count", default=len(self._get_val(a, "sources", "collected_data", default=[]))))
                for a in analyses
            ],
            ["**架构核心摘要**"] + [
                str(self._get_val(a, "architecture_summary", default="暂无摘要"))[:120] + "..."
                if len(str(self._get_val(a, "architecture_summary", default=""))) > 120
                else str(self._get_val(a, "architecture_summary", default="暂无摘要"))
                for a in analyses
            ],
        ]

        table_md = [
            "| " + " | ".join(table_headers) + " |",
            "| " + " | ".join(table_sep) + " |",
        ]
        for row in overview_rows:
            clean_row = [cell.replace("\n", " ").replace("|", "\\|") for cell in row]
            table_md.append("| " + " | ".join(clean_row) + " |")
        sections.append("\n".join(table_md) + "\n")

        # 3. 架构维度横向对比
        sections.append("## 2. 关键架构维度对比\n")

        # 汇总各分析覆盖的所有维度
        all_dim_labels: list[str] = []
        app_dim_maps: list[dict[str, Any]] = []

        for a in analyses:
            dims = self._get_val(a, "common_dimensions", default=[])
            dim_map = {}
            for d in dims:
                label = self._get_val(d, "dimension_label", "label", "dimension_name", "dimension", default="未知维度")
                dim_map[label] = d
                if label not in all_dim_labels:
                    all_dim_labels.append(label)
            app_dim_maps.append(dim_map)

        if all_dim_labels:
            dim_table_headers = ["架构维度"] + app_names
            dim_table_sep = [":---"] + [":---"] * len(app_names)
            dim_table_rows = []

            for label in all_dim_labels:
                row_cells = [f"**{label}**"]
                for dim_map in app_dim_maps:
                    dim_data = dim_map.get(label)
                    if dim_data:
                        summary = self._get_val(dim_data, "summary", default="")
                        takeaways = self._get_val(dim_data, "takeaways", "key_takeaways", default=[])
                        cell_content = summary
                        if takeaways and isinstance(takeaways, list) and takeaways[0]:
                            cell_content += f"<br>• *{takeaways[0]}*"
                        row_cells.append(cell_content)
                    else:
                        row_cells.append("*未明确覆盖*")
                dim_table_rows.append(row_cells)

            dim_md = [
                "| " + " | ".join(dim_table_headers) + " |",
                "| " + " | ".join(dim_table_sep) + " |",
            ]
            for row in dim_table_rows:
                clean_row = [cell.replace("\n", " ").replace("|", "\\|") for cell in row]
                dim_md.append("| " + " | ".join(clean_row) + " |")
            sections.append("\n".join(dim_md) + "\n")
        else:
            sections.append("*暂无共性维度数据可对比。*\n")

        # 4. 关键洞察对比
        sections.append("## 3. 各应用关键洞察\n")
        for i, a in enumerate(analyses):
            name = app_names[i]
            insights = self._get_val(a, "key_insights", default=[])
            sections.append(f"### {name}")
            if insights and isinstance(insights, list):
                for idx, insight in enumerate(insights, 1):
                    sections.append(f"{idx}. {insight}")
            elif insights:
                sections.append(f"1. {insights}")
            else:
                sections.append("*暂无关键洞察*")
            sections.append("")

        # 5. 分析说明
        sections.append("## 4. 分析说明\n")
        sections.append(
            "> **说明**：本对比报告基于自动化采集的各产品公开信息（技术文章、开源代码、架构解析等）生成，"
            "旨在提炼不同产品在 Harness 架构设计上的差异与共性，为架构选型与系统设计提供参考。\n"
        )

        return "\n".join(sections)
