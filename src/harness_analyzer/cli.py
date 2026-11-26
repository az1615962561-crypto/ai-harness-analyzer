"""AI Harness Analyzer CLI"""
import asyncio
import json as json_module
import os
import shutil
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from harness_analyzer.logging_utils import configure_logging

app = typer.Typer(
    name="harness",
    help="🔍 AI Harness Architecture Analyzer - 分析 AI 应用背后的 Harness 架构",
    rich_markup_mode="rich",
)
cache_app = typer.Typer(help="管理本地 SQLite 分析结果缓存")
app.add_typer(cache_app, name="cache")
console = Console()


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="开启详细调试日志"),
):
    """AI Harness Architecture Analyzer CLI"""
    configure_logging(verbose=verbose)

CATEGORY_ICONS = {
    "engineering": "🔧",
    "data": "📊",
    "knowledge": "🧠",
    "creative": "🎨",
    "automation": "🤖",
}


def _cat_info(category) -> tuple[str, str, str]:
    """返回 (category_value, category_label, icon)"""
    cat_val = category.value if hasattr(category, "value") else str(category)
    cat_lbl = category.label if hasattr(category, "label") else cat_val
    icon = CATEGORY_ICONS.get(cat_val, "🤖")
    return cat_val, cat_lbl, icon


@app.command(name="list")
def list_apps(
    category: str = typer.Option(None, "--category", "-c", help="按分类筛选 (engineering/data/knowledge/creative/automation)"),
    tag: str = typer.Option(None, "--tag", "-t", help="按标签筛选"),
):
    """列出所有已注册的 AI 应用"""
    from harness_analyzer.registry.loader import AppRegistry

    registry = AppRegistry()
    apps = registry.list_apps(category=category, tag=tag)

    if not apps:
        console.print("[yellow]未找到匹配的应用[/yellow]")
        return

    table = Table(title="🔍 AI 应用注册表", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim")
    table.add_column("名称", style="bold")
    table.add_column("分类", justify="center")
    table.add_column("描述")
    table.add_column("信息丰富度", justify="center")

    for a in sorted(apps, key=lambda x: (str(x.category), x.name)):
        _, cat_lbl, icon = _cat_info(a.category)
        stars = "★" * a.info_richness + "☆" * (5 - a.info_richness)
        table.add_row(a.name, a.display_name, f"{icon} {cat_lbl}", a.description, stars)

    console.print(table)
    console.print(f"\n共 {len(apps)} 个应用")


@app.command()
def search(query: str = typer.Argument(help="搜索关键词")):
    """按关键词搜索注册表中的 AI 应用"""
    from harness_analyzer.registry.loader import AppRegistry

    registry = AppRegistry()
    apps = registry.search(query)
    if not apps:
        console.print(f"[yellow]未找到包含 '{query}' 的应用[/yellow]")
        return

    for a in apps:
        _, cat_lbl, icon = _cat_info(a.category)
        console.print(f"• {icon} [bold]{a.display_name}[/bold] (`{a.name}`, {cat_lbl}) - {a.description}")


@app.command()
def info(app_name: str = typer.Argument(help="应用名称")):
    """查看应用详细信息、维度权重与专属拆解维度"""
    from harness_analyzer.registry.loader import AppRegistry
    from harness_analyzer.models.dimension import CATEGORY_DIMENSIONS, DIMENSION_WEIGHTS, CommonDimension

    registry = AppRegistry()
    a = registry.get_app(app_name)
    if not a:
        console.print(f"[red]未找到应用: {app_name}[/red]")
        console.print("使用 [bold]harness list[/bold] 查看所有可用应用，或直接运行 [bold]harness analyze[/bold] 进行全网探测")
        raise typer.Exit(1)

    cat_val, cat_lbl, icon = _cat_info(a.category)
    stars = "★" * a.info_richness + "☆" * (5 - a.info_richness)

    info_text = (
        f"[bold]{a.display_name}[/bold]  {icon} {cat_lbl}\n\n"
        f"{a.description}\n\n"
        f"网站: {a.website or 'N/A'}\n"
        f"GitHub: {a.github_url or 'N/A'}\n"
        f"信息丰富度: {stars}\n"
        f"标签: {', '.join(str(t.value if hasattr(t, 'value') else t) for t in a.tags)}\n\n"
        f"[bold]信息来源:[/bold]"
    )
    for src in a.info_sources:
        info_text += f"\n  • [{src.source_type}] {src.description} - {src.url}"

    weights = DIMENSION_WEIGHTS.get(cat_val, {})
    info_text += "\n\n[bold]共性维度权重:[/bold]"
    for dim in CommonDimension:
        w = weights.get(dim.value, 3)
        bar = "█" * w + "░" * (5 - w)
        info_text += f"\n  {bar} {dim.label}"

    spec_dims = CATEGORY_DIMENSIONS.get(cat_val, [])
    if spec_dims:
        info_text += "\n\n[bold]品类专属维度:[/bold]"
        for sd in spec_dims:
            info_text += f"\n  • {sd.label}"

    console.print(Panel(info_text, title=f"{icon} {a.display_name}", border_style="cyan"))


@app.command()
def analyze(
    app_name: str = typer.Argument(help="应用名称"),
    depth: str = typer.Option("full", "--depth", "-d", help="分析深度: quick/full"),
    lang: str = typer.Option("zh", "--lang", help="提问语言（默认 zh，自动执行「提问语言 + 英语」双重检索）"),
    dimensions: str = typer.Option(None, "--dimensions", help="指定分析的共性维度（逗号分隔）"),
    github: str = typer.Option(None, "--github", "-g", help="自定义或补充 GitHub 仓库地址"),
    url: str = typer.Option(None, "--url", "-u", help="自定义或补充官网/技术博客 URL"),
    local_app: Path = typer.Option(None, "--local-app", "-l", help="本地客户端解包目录或 app.asar（逆向提取 Prompt/Rules）"),
    use_rea: bool = typer.Option(False, "--use-rea", help="显式启用 rea-agents 对本地 ASAR/JS 应用做深度结构化逆向（需 Node.js）"),
    offline: bool = typer.Option(False, "--offline", help="使用专家基准知识库离线分析（无需配置 API Key）"),
    output_dir: Path = typer.Option(None, "--output-dir", "-O", help="自定义报告输出目录（覆盖 HARNESS_REPORTS_DIR）"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="开启详细调试日志"),
):
    """分析 AI 应用的 Harness 架构（支持预置应用、未知应用全网探测及本地逆向解包）"""
    if verbose:
        configure_logging(verbose=True)
    from harness_analyzer.config import get_settings
    from harness_analyzer.registry.loader import AppRegistry
    from harness_analyzer.models.app import AIApp, AppCategory, InfoSource
    from harness_analyzer.models.harness import HarnessAnalysis
    from harness_analyzer.collectors.github import GitHubCollector
    from harness_analyzer.collectors.blog import BlogCollector
    from harness_analyzer.collectors.search import WebSearchCollector
    from harness_analyzer.collectors.reverse_eng import ReverseEngineeringCollector
    from harness_analyzer.collectors.reviews import UserReviewCollector
    from harness_analyzer.collectors.query_planner import BilingualQueryPlanner
    from harness_analyzer.analyzer.dimensions import CommonDimensionExtractor
    from harness_analyzer.analyzer.specialized import get_specialized_analyzer
    from harness_analyzer.analyzer.intermediate import IntermediateArtifactBuilder
    from harness_analyzer.analyzer.pm_guidance import PMGuidanceExtractor
    from harness_analyzer.analyzer.offline import OfflineBenchmarkProvider
    from harness_analyzer.output.markdown import MarkdownReportGenerator
    from harness_analyzer.output.diagram import DiagramGenerator
    from harness_analyzer.storage.cache import AnalysisCache

    settings = get_settings()
    registry = AppRegistry()
    app_obj = registry.get_app(app_name)
    is_adhoc = False

    if not app_obj:
        is_adhoc = True
        console.print(f"[yellow]🔍 应用 '{app_name}' 未在本地预置注册表中，启动【全网动态搜索与架构探测引擎】...[/yellow]")
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

    cat_val, cat_lbl, icon = _cat_info(app_obj.category)

    use_offline = offline
    if not settings.api_key:
        if OfflineBenchmarkProvider.has_benchmark(app_obj.name) or offline:
            use_offline = True
            console.print("[cyan]ℹ️ 未检测到 API Key，自动启用专家基准架构知识库进行分析...[/cyan]")
        else:
            if is_adhoc:
                console.print(f"[red]错误: 应用 '{app_name}' 为全新小众应用，全网动态分析需要配置大模型 API Key[/red]")
                console.print("请在 .env 中设置 GEMINI_API_KEY、OPENAI_API_KEY 或 ANTHROPIC_API_KEY 以便执行动态搜索与架构提取。")
                raise typer.Exit(1)
            console.print("[red]错误: 未配置 API Key[/red]")
            console.print("请在 .env 文件中设置 GEMINI_API_KEY、OPENAI_API_KEY 或 ANTHROPIC_API_KEY")
            console.print("或者针对已预置的应用使用: [bold]harness analyze <app> --offline[/bold]")
            raise typer.Exit(1)

    console.print(f"\n{icon} 开始分析 [bold]{app_obj.display_name}[/bold] ({cat_lbl}) 的 Harness 架构...\n")

    if use_offline:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("📚 提取专家架构基准知识...", total=None)
            analysis = OfflineBenchmarkProvider.get_analysis(app_obj)
            if not analysis.mermaid_diagram:
                analysis.mermaid_diagram = DiagramGenerator().generate(analysis)
            progress.update(task, description="✅ 架构数据与中间产物构建完成")
    else:
        collected_texts: list[str] = []
        raw_sources: list[str] = []
        raw_corpus_parts: list[str] = []
        primary_corpus_parts: list[str] = []
        review_items = []

        _PRIMARY_SOURCE_TYPES = {
            "github_readme", "github_tree", "github_source",
            "blog", "blog_article", "docs", "documentation", "product_page",
            "re_repository", "github_re_search", "local_reverse_engineering",
        }

        from harness_analyzer.analyzer.llm import LLMClient
        from harness_analyzer.analyzer.evidence import verify_all_dimensions
        from harness_analyzer.analyzer.fact_sheet import FactSheetExtractor
        from harness_analyzer.collectors.web_utils import DomainRateLimiter
        llm = LLMClient()

        bilingual_names, planned_queries = BilingualQueryPlanner.plan_search_queries(
            app_obj.display_name, question_lang=lang, llm=llm
        )
        shared_limiter = DomainRateLimiter(min_interval=1.0, max_concurrency=4)
        searcher = WebSearchCollector(question_lang=lang, rate_limiter=shared_limiter)
        review_collector = UserReviewCollector(question_lang=lang)
        gh = GitHubCollector()
        blog = BlogCollector(rate_limiter=shared_limiter)
        re_collector = ReverseEngineeringCollector(local_app_path=local_app, use_rea=use_rea)

        collected_items = []
        refill_triggered = False

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task(
                f"📡 正在执行「{lang} + en」双语全网检索与五路采集 ({bilingual_names.get('local')} / {bilingual_names.get('en')})...",
                total=None,
            )

            async def collect_with_refill():
                nonlocal refill_triggered
                results = []
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

                return results, cov_items

            try:
                collected_items, all_cov_items = asyncio.run(collect_with_refill())
                for c in collected_items:
                    collected_texts.append(f"[{c.source_type}] {c.title}\n{c.content[:4500]}")
                    raw_corpus_parts.append(c.content)
                    if c.source_type in _PRIMARY_SOURCE_TYPES:
                        primary_corpus_parts.append(c.content)
                    if c.source_type == "user_review":
                        review_items.append(c)
                    if c.source_url and c.source_url not in raw_sources:
                        raw_sources.append(c.source_url)
            except Exception as e:
                all_cov_items = []
                console.print(f"[yellow]采集数据时出错: {e}，将基于已知公开信息继续分析[/yellow]")

            from harness_analyzer.models.harness import BlockedSource
            blocked_all: list[BlockedSource] = list(shared_limiter.blocked_records)
            for item in [*searcher.last_blocked_sources, *gh.last_blocked_sources]:
                if isinstance(item, BlockedSource):
                    blocked_all.append(item)
                elif isinstance(item, dict):
                    blocked_all.append(BlockedSource(**item))

            search_coverage = BilingualQueryPlanner.build_coverage_report(
                all_cov_items,
                question_lang=lang,
                bilingual_names=bilingual_names,
                refill_triggered=refill_triggered,
                blocked_sources=blocked_all,
            )
            progress.update(
                task,
                description=(
                    f"✅ 采集完成 ({len(collected_texts)} 条信源, {len(review_items)} 组用户评论, "
                    f"覆盖度 {search_coverage.coverage_score:.0%}, 拦截熔断 {len(blocked_all)})"
                ),
            )

        collected_data = "\n\n---\n\n".join(collected_texts) if collected_texts else "全网公开信源较少，请基于已知信息进行严谨推断并降低置信度。"
        raw_corpus = "\n\n".join(raw_corpus_parts)
        primary_corpus = "\n\n".join(primary_corpus_parts)

        if is_adhoc and collected_texts:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                c_task = progress.add_task("🔍 动态识别该应用的 Harness 业务品类...", total=None)
                classify_prompt = (
                    f"请分析 AI 应用 '{app_obj.display_name}' 属于以下哪一类：\n"
                    f"- engineering (工程型): 代码编辑/终端执行/IDE工具\n"
                    f"- data (数据型): NL2SQL/BI分析/表格查询\n"
                    f"- knowledge (知识型): RAG搜索/文档问答/笔记分析\n"
                    f"- creative (创作型): 图像/UI/PPT/营销文案生成\n"
                    f"- automation (自动化型): 多步工作流/自律Agent/任务自动化\n\n"
                    f"信源参考：\n{collected_data[:1500]}\n\n"
                    f"只输出一个分类英文单词 (engineering/data/knowledge/creative/automation):"
                )
                try:
                    resp = llm.analyze(classify_prompt).strip().lower()
                    for cat_candidate in AppCategory:
                        if cat_candidate.value in resp:
                            app_obj.category = cat_candidate
                            cat_val, cat_lbl, icon = _cat_info(cat_candidate)
                            break
                    progress.update(c_task, description=f"🎯 自动定性识别为: 【{icon} {cat_lbl}】AI 应用")
                except Exception:
                    progress.update(c_task, description="⚠️ 自动分类完成")

        app_info = (
            f"应用名称: {app_obj.display_name}\n"
            f"分类: {cat_val} ({cat_lbl})\n"
            f"描述: {app_obj.description}\n"
            f"网站: {app_obj.website}\n"
            f"GitHub: {app_obj.github_url}"
        )

        only_dims = [d.strip() for d in dimensions.split(",") if d.strip()] if dimensions else None

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("🧪 Stage 1: 并发提炼高密度技术事实底座 (Fact Sheet)...", total=None)

            from harness_analyzer.analyzer.patterns import PatternMatcher

            extractor = CommonDimensionExtractor(llm)
            spec_analyzer = get_specialized_analyzer(cat_val, llm)
            pattern_matcher = PatternMatcher(llm)

            async def run_two_stage_analysis():
                fact_sheet = await FactSheetExtractor(llm).build_fact_sheet(
                    app_obj.display_name, collected_items
                )
                progress.update(task, description=f"⚡ Stage 2: 并发拆解 9 共性 + {cat_lbl}专属 5 维度 + 架构模式...")
                c_dims, s_dims, matched_patterns = await asyncio.gather(
                    extractor.aextract_all(
                        app_info,
                        fact_sheet,
                        category=cat_val,
                        depth=depth,
                        only_dimensions=only_dims,
                        max_concurrency=settings.max_concurrency,
                    ),
                    spec_analyzer.aanalyze(app_info, fact_sheet, max_concurrency=settings.max_concurrency),
                    pattern_matcher.amatch(app_info, fact_sheet),
                )
                return c_dims, s_dims, matched_patterns

            common_dims, spec_dims, matched_patterns = asyncio.run(run_two_stage_analysis())

            progress.update(task, description="🛡️ 按联系程度执行分维度独立 Guard 校验（比对原始语料）...")
            common_dims, spec_dims = verify_all_dimensions(
                common_dims,
                spec_dims,
                raw_corpus,
                category=cat_val,
                primary_corpus=primary_corpus,
            )

            progress.update(task, description="📦 合成中间产物（含检索覆盖度与权威用户评论）...")
            intermediate_artifact = IntermediateArtifactBuilder(llm).build(
                app_name=app_obj.name,
                category=cat_val,
                common_dims=common_dims,
                specialized_dims=spec_dims,
                review_items=review_items,
                search_coverage=search_coverage,
            )

            progress.update(task, description="🎯 基于中间产物转化为产品经理方案指导 (PM Guidance)...")
            pm_guidance = PMGuidanceExtractor(llm).extract_from_artifact(app_info, intermediate_artifact)
            progress.update(task, description="✅ 中间产物、分维度 Guard 与 PM 方案拆解完成")

        all_verified_dims = [*common_dims, *spec_dims]
        analysis = HarnessAnalysis(
            app_name=app_obj.name,
            app_display_name=app_obj.display_name,
            category=cat_val,
            intermediate_artifact=intermediate_artifact,
            pm_guidance=pm_guidance,
            common_dimensions=common_dims,
            specialized_dimensions=spec_dims,
            matched_patterns=matched_patterns,
            architecture_summary=f"{app_obj.display_name} 是一个{cat_lbl}类 AI 应用",
            key_insights=[d.summary for d in common_dims if d.confidence >= 3][:5],
            raw_sources=raw_sources,
            source_count=len(collected_texts),
            confidence_overall=round(sum(d.confidence for d in all_verified_dims) / max(len(all_verified_dims), 1)),
        )
        analysis.mermaid_diagram = DiagramGenerator().generate(analysis)

    target_reports_dir = output_dir or settings.reports_dir

    # Cache (确保存入字符串分类名)
    cache = AnalysisCache(settings.cache_dir)
    cache.save(app_obj.name, cat_val, analysis.model_dump_json())

    # 持久化保存结构化中间产物 (.intermediate.json)
    intermediate_path = None
    if analysis.intermediate_artifact is not None:
        intermediate_path = IntermediateArtifactBuilder.save_to_disk(
            analysis.intermediate_artifact, target_reports_dir, app_obj.name
        )

    # Generate report
    report_gen = MarkdownReportGenerator()
    report_text = report_gen.generate(analysis)

    target_reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = target_reports_dir / f"{app_obj.name}.md"
    report_path.write_text(report_text, encoding="utf-8")

    console.print("\n[green]✅ 分析完成！[/green]")
    if intermediate_path:
        console.print(f"📦 中间产物已保存到: [bold]{intermediate_path}[/bold]")
    console.print(f"📄 报告已保存到: [bold]{report_path}[/bold]")

    if analysis.key_insights:
        console.print("\n[bold]关键洞察:[/bold]")
        for i, insight in enumerate(analysis.key_insights, 1):
            console.print(f"  {i}. {insight}")


@app.command()
def compare(
    apps: list[str] = typer.Argument(help="要对比的应用名称（至少2个）"),
    output: Path = typer.Option(None, "--output", "-o", help="输出文件路径"),
    output_dir: Path = typer.Option(None, "--output-dir", "-O", help="对比报告输出目录（未指定 -o 时生效）"),
):
    """对比多个 AI 应用的 Harness 架构"""
    from harness_analyzer.config import get_settings
    from harness_analyzer.registry.loader import AppRegistry
    from harness_analyzer.storage.cache import AnalysisCache
    from harness_analyzer.models.harness import HarnessAnalysis
    from harness_analyzer.output.comparison import ComparisonReportGenerator

    if len(apps) < 2:
        console.print("[red]至少需要 2 个应用进行对比[/red]")
        raise typer.Exit(1)

    settings = get_settings()
    registry = AppRegistry()
    cache = AnalysisCache(settings.cache_dir)

    analyses = []
    for raw_name in apps:
        app_obj = registry.get_app(raw_name)
        canonical_name = app_obj.name if app_obj else raw_name.lower().replace(" ", "-")
        cached = cache.get(canonical_name) or cache.get(raw_name)
        if not cached:
            console.print(f"[yellow]{raw_name} 尚未分析，请先运行: harness analyze {canonical_name}[/yellow]")
            raise typer.Exit(1)
        analyses.append(HarnessAnalysis(**cached))

    gen = ComparisonReportGenerator()
    report_text = gen.generate(analyses)

    out_path = output or ((output_dir or settings.reports_dir) / "comparison.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_text, encoding="utf-8")

    console.print(f"[green]✅ 对比报告已保存到: {out_path}[/green]")


@app.command()
def doctor():
    """检查运行环境、API 密钥、搜索引擎、逆向工具与内置注册表就绪状态"""
    from harness_analyzer.config import get_settings
    from harness_analyzer.registry.loader import AppRegistry
    from harness_analyzer.analyzer.patterns import load_pattern_catalog

    settings = get_settings()
    registry = AppRegistry()
    apps = registry.list_apps()
    patterns = load_pattern_catalog()

    table = Table(title="🩺 AI Harness Analyzer 环境自检 (Doctor)", show_header=True, header_style="bold cyan")
    table.add_column("检查项", style="bold")
    table.add_column("状态", justify="center")
    table.add_column("详情")

    py_ver = sys.version.split()[0]
    py_ok = sys.version_info >= (3, 11)
    table.add_row("Python 版本", "✅" if py_ok else "⚠️", f"{py_ver} (建议 >= 3.11)")

    llm_keys = [k for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY") if os.getenv(k)]
    table.add_row(
        "LLM API Key",
        "✅" if llm_keys else "⚠️",
        ", ".join(llm_keys) if llm_keys else "未配置（仅可运行 --offline 模式；在线分析需至少配置一个）",
    )
    table.add_row(
        "默认模型与并发",
        "ℹ️",
        f"{settings.llm_model} (max_concurrency={settings.max_concurrency}, retries={settings.llm_max_retries})",
    )

    tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
    try:
        import ddgs  # noqa: F401
        ddgs_ver = getattr(ddgs, "__version__", "installed")
        ddgs_status = f"ddgs {ddgs_ver}"
    except Exception:
        ddgs_status = "未安装 ddgs"
    table.add_row(
        "全网搜索引擎",
        "✅" if tavily_ok else "ℹ️",
        f"Tavily API {'已配置' if tavily_ok else '未配置（将自动使用 ' + ddgs_status + '）'}",
    )

    gh_ok = bool(os.getenv("GITHUB_TOKEN"))
    table.add_row(
        "GitHub Token",
        "✅" if gh_ok else "ℹ️",
        "已配置（高限额 5000 req/h）" if gh_ok else "未配置（匿名限额 60 req/h）",
    )

    node_bin = shutil.which("node")
    npx_bin = shutil.which("npx")
    rea_bin = shutil.which("rea")
    re_details = []
    if rea_bin:
        re_details.append(f"rea={rea_bin}")
    elif node_bin and npx_bin:
        re_details.append(f"node+npx 就绪（支持 --use-rea）")
    else:
        re_details.append("未检测到 node/npx/rea（仅启用内置静态 ASAR/规则扫描，不影响常规分析）")
    table.add_row("本地逆向工具链", "✅" if (rea_bin or (node_bin and npx_bin)) else "ℹ️", "; ".join(re_details))

    table.add_row("内置应用注册表", "✅" if apps else "❌", f"{len(apps)} 个应用 ({registry.registry_path})")
    table.add_row("架构模式目录", "✅" if patterns else "⚠️", f"{len(patterns)} 个参考模式")
    table.add_row("缓存与报告目录", "ℹ️", f"cache={settings.cache_dir} | reports={settings.reports_dir}")

    console.print(table)


@cache_app.command("list")
def cache_list():
    """列出本地已缓存的分析结果"""
    from harness_analyzer.config import get_settings
    from harness_analyzer.storage.cache import AnalysisCache

    settings = get_settings()
    cache = AnalysisCache(settings.cache_dir)
    rows = cache.list_cached()
    if not rows:
        console.print(f"[yellow]缓存目录 {settings.cache_dir} 中暂无分析记录[/yellow]")
        return

    table = Table(title="🗄️ 本地分析缓存", show_header=True, header_style="bold cyan")
    table.add_column("应用 ID", style="bold")
    table.add_column("分类", justify="center")
    table.add_column("缓存时间 (UTC)")
    for row in rows:
        table.add_row(row["app_name"], str(row.get("category") or "-"), str(row.get("analyzed_at") or "-"))
    console.print(table)
    console.print(f"共 {len(rows)} 条缓存记录")


@cache_app.command("clear")
def cache_clear(
    app_name: str = typer.Argument(None, help="指定清除的应用 ID；留空则清空全部缓存"),
):
    """清除指定应用或全部本地分析缓存"""
    from harness_analyzer.config import get_settings
    from harness_analyzer.storage.cache import AnalysisCache

    settings = get_settings()
    cache = AnalysisCache(settings.cache_dir)
    if app_name:
        cache.clear(app_name)
        console.print(f"[green]✅ 已清除 '{app_name}' 的本地缓存[/green]")
    else:
        cache.clear()
        console.print("[green]✅ 已清空全部本地分析缓存[/green]")


@app.command()
def report(
    app_name: str = typer.Argument(help="应用名称"),
    format: str = typer.Option("markdown", "--format", "-f", help="输出格式: markdown/json"),
):
    """查看已缓存的分析报告"""
    from harness_analyzer.config import get_settings
    from harness_analyzer.registry.loader import AppRegistry
    from harness_analyzer.storage.cache import AnalysisCache
    from harness_analyzer.models.harness import HarnessAnalysis
    from harness_analyzer.output.markdown import MarkdownReportGenerator

    settings = get_settings()
    registry = AppRegistry()
    app_obj = registry.get_app(app_name)
    canonical_name = app_obj.name if app_obj else app_name.lower().replace(" ", "-")

    cache = AnalysisCache(settings.cache_dir)
    cached = cache.get(canonical_name) or cache.get(app_name)

    if not cached:
        console.print(f"[yellow]{app_name} 尚未分析[/yellow]")
        console.print(f"请先运行: [bold]harness analyze {canonical_name}[/bold]")
        raise typer.Exit(1)

    if format == "json":
        console.print(json_module.dumps(cached, indent=2, ensure_ascii=False))
    else:
        analysis = HarnessAnalysis(**cached)
        gen = MarkdownReportGenerator()
        console.print(gen.generate(analysis))


if __name__ == "__main__":
    app()
