"""AI Harness Analyzer CLI"""
import asyncio
from pathlib import Path
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

app = typer.Typer(
    name="harness",
    help="🔍 AI Harness Architecture Analyzer",
    rich_markup_mode="rich",
)
console = Console()

CATEGORY_ICONS = {
    "engineering": "🔧",
    "data": "📊",
    "knowledge": "🧠",
    "creative": "🎨",
    "automation": "🤖",
}


@app.command(name="list")
def list_apps(
    category: str = typer.Option(None, "--category", "-c", help="按分类筛选"),
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
    table.add_column("名称", style="bold")
    table.add_column("分类", justify="center")
    table.add_column("描述")
    table.add_column("信息丰富度", justify="center")
    
    for a in sorted(apps, key=lambda x: x.category):
        cat_val = a.category.value if hasattr(a.category, "value") else str(a.category)
        cat_lbl = a.category.label if hasattr(a.category, "label") else cat_val
        icon = CATEGORY_ICONS.get(cat_val, "")
        stars = "★" * a.info_richness + "☆" * (5 - a.info_richness)
        table.add_row(a.display_name, f"{icon} {cat_lbl}", a.description, stars)
    
    console.print(table)
    console.print(f"\n共 {len(apps)} 个应用")


@app.command()
def info(app_name: str = typer.Argument(help="应用名称")):
    """查看应用详细信息"""
    from harness_analyzer.registry.loader import AppRegistry
    from harness_analyzer.models.dimension import CATEGORY_DIMENSIONS, DIMENSION_WEIGHTS, CommonDimension
    
    registry = AppRegistry()
    a = registry.get_app(app_name)
    if not a:
        console.print(f"[red]未找到应用: {app_name}[/red]")
        console.print("使用 [bold]harness list[/bold] 查看所有可用应用")
        raise typer.Exit(1)
    
    cat_val = a.category.value if hasattr(a.category, "value") else str(a.category)
    cat_lbl = a.category.label if hasattr(a.category, "label") else cat_val
    icon = CATEGORY_ICONS.get(cat_val, "")
    stars = "★" * a.info_richness + "☆" * (5 - a.info_richness)
    
    info_text = f"""[bold]{a.display_name}[/bold]  {icon} {cat_lbl}
    
{a.description}

网站: {a.website or 'N/A'}
GitHub: {a.github_url or 'N/A'}
信息丰富度: {stars}
标签: {', '.join(str(t.value if hasattr(t, 'value') else t) for t in a.tags)}

[bold]信息来源:[/bold]"""
    for src in a.info_sources:
        info_text += f"\n  • [{src.source_type}] {src.description} - {src.url}"
    
    # Show applicable dimensions
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
    depth: str = typer.Option("quick", "--depth", "-d", help="分析深度: quick/full"),
    offline: bool = typer.Option(False, "--offline", help="使用专家基准知识库离线分析（无需配置 API Key）"),
):
    """分析 AI 应用的 Harness 架构"""
    from harness_analyzer.config import get_settings
    from harness_analyzer.registry.loader import AppRegistry
    from harness_analyzer.models.dimension import DIMENSION_WEIGHTS
    from harness_analyzer.models.harness import HarnessAnalysis
    from harness_analyzer.collectors.github import GitHubCollector
    from harness_analyzer.collectors.blog import BlogCollector
    from harness_analyzer.analyzer.dimensions import CommonDimensionExtractor
    from harness_analyzer.analyzer.specialized import get_specialized_analyzer
    from harness_analyzer.analyzer.offline import OfflineBenchmarkProvider
    from harness_analyzer.output.markdown import MarkdownReportGenerator
    from harness_analyzer.storage.cache import AnalysisCache
    
    settings = get_settings()
    registry = AppRegistry()
    app_obj = registry.get_app(app_name)
    if not app_obj:
        console.print(f"[red]未找到应用: {app_name}[/red]")
        raise typer.Exit(1)

    cat_val = app_obj.category.value if hasattr(app_obj.category, "value") else str(app_obj.category)
    cat_lbl = app_obj.category.label if hasattr(app_obj.category, "label") else cat_val
    icon = CATEGORY_ICONS.get(cat_val, "")
    
    # 检查是否使用离线专家基准模式
    use_offline = offline
    if not settings.api_key:
        if OfflineBenchmarkProvider.has_benchmark(app_obj.name) or offline:
            use_offline = True
            console.print("[cyan]ℹ️ 未检测到 API Key，自动启用专家基准架构知识库进行分析...[/cyan]")
        else:
            console.print("[red]错误: 未配置 API Key[/red]")
            console.print("请在 .env 文件中设置 GEMINI_API_KEY、OPENAI_API_KEY 或 ANTHROPIC_API_KEY")
            console.print("或者针对已预置的应用使用: [bold]harness analyze <app> --offline[/bold]")
            raise typer.Exit(1)

    console.print(f"\n{icon} 开始分析 [bold]{app_obj.display_name}[/bold] ({cat_lbl}) 的 Harness 架构...\n")
    
    if use_offline:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("📚 提取专家架构基准知识...", total=None)
            analysis = OfflineBenchmarkProvider.get_analysis(app_obj)
            progress.update(task, description="✅ 架构数据构建完成")
    else:
        # Collect data
        collected_texts = []
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("📡 采集数据...", total=None)
            
            async def collect():
                results = []
                gh = GitHubCollector()
                blog = BlogCollector()
                results.extend(await gh.collect(app_obj))
                results.extend(await blog.collect(app_obj))
                return results
            
            try:
                collected = asyncio.run(collect())
                for c in collected:
                    collected_texts.append(f"[{c.source_type}] {c.title}\n{c.content[:2000]}")
            except Exception as e:
                console.print(f"[yellow]采集数据时出错: {e}，将使用有限信息继续分析[/yellow]")
            
            progress.update(task, description="✅ 数据采集完成")
        
        collected_data = "\n\n---\n\n".join(collected_texts) if collected_texts else "无额外采集数据，请基于已知公开信息分析。"
        app_info = f"应用名称: {app_obj.display_name}\n分类: {cat_val}\n描述: {app_obj.description}\n网站: {app_obj.website}\nGitHub: {app_obj.github_url}"
        
        # Run analysis
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("🧠 AI 分析中...", total=None)
            
            from harness_analyzer.analyzer.llm import LLMClient
            llm = LLMClient()
            
            # Common dimensions
            extractor = CommonDimensionExtractor(llm)
            common_dims = extractor.extract_all(app_info, collected_data, category=cat_val)
            progress.update(task, description="🧠 共性维度分析完成，开始品类专属分析...")
            
            # Specialized dimensions
            spec_analyzer = get_specialized_analyzer(cat_val, llm)
            spec_dims = spec_analyzer.analyze(app_info, collected_data)
            progress.update(task, description="✅ 分析完成")
        
        # Build analysis result
        analysis = HarnessAnalysis(
            app_name=app_obj.name,
            app_display_name=app_obj.display_name,
            category=cat_val,
            common_dimensions=common_dims,
            specialized_dimensions=spec_dims,
            architecture_summary=f"{app_obj.display_name} 是一个{cat_lbl}类 AI 应用",
            key_insights=[d.summary for d in common_dims if d.confidence >= 3][:5],
            source_count=len(collected_texts),
            confidence_overall=round(sum(d.confidence for d in common_dims) / max(len(common_dims), 1)),
        )
    
    # Cache
    cache = AnalysisCache(settings.cache_dir)
    cache.save(app_obj.name, app_obj.category, analysis.model_dump_json())
    
    # Generate report
    report_gen = MarkdownReportGenerator()
    report = report_gen.generate(analysis)
    
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = settings.reports_dir / f"{app_obj.name}.md"
    report_path.write_text(report, encoding="utf-8")
    
    console.print(f"\n[green]✅ 分析完成！[/green]")
    console.print(f"📄 报告已保存到: [bold]{report_path}[/bold]")
    
    # Print summary
    console.print(f"\n[bold]关键洞察:[/bold]")
    for i, insight in enumerate(analysis.key_insights, 1):
        console.print(f"  {i}. {insight}")


@app.command()
def compare(
    apps: list[str] = typer.Argument(help="要对比的应用名称（至少2个）"),
    output: Path = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """对比多个 AI 应用的 Harness 架构"""
    from harness_analyzer.config import get_settings
    from harness_analyzer.storage.cache import AnalysisCache
    from harness_analyzer.models.harness import HarnessAnalysis
    from harness_analyzer.output.comparison import ComparisonReportGenerator
    
    if len(apps) < 2:
        console.print("[red]至少需要 2 个应用进行对比[/red]")
        raise typer.Exit(1)
    
    settings = get_settings()
    cache = AnalysisCache(settings.cache_dir)
    
    analyses = []
    for name in apps:
        cached = cache.get(name)
        if not cached:
            console.print(f"[yellow]{name} 尚未分析，请先运行: harness analyze {name}[/yellow]")
            raise typer.Exit(1)
        analyses.append(HarnessAnalysis(**cached))
    
    gen = ComparisonReportGenerator()
    report = gen.generate(analyses)
    
    out_path = output or settings.reports_dir / "comparison.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    
    console.print(f"[green]✅ 对比报告已保存到: {out_path}[/green]")


@app.command()
def report(
    app_name: str = typer.Argument(help="应用名称"),
    format: str = typer.Option("markdown", "--format", "-f", help="输出格式: markdown/json"),
):
    """查看已缓存的分析报告"""
    import json as json_module
    from harness_analyzer.config import get_settings
    from harness_analyzer.storage.cache import AnalysisCache
    from harness_analyzer.models.harness import HarnessAnalysis
    from harness_analyzer.output.markdown import MarkdownReportGenerator
    
    settings = get_settings()
    cache = AnalysisCache(settings.cache_dir)
    cached = cache.get(app_name)
    
    if not cached:
        console.print(f"[yellow]{app_name} 尚未分析[/yellow]")
        console.print(f"请先运行: [bold]harness analyze {app_name}[/bold]")
        raise typer.Exit(1)
    
    if format == "json":
        console.print(json_module.dumps(cached, indent=2, ensure_ascii=False))
    else:
        analysis = HarnessAnalysis(**cached)
        gen = MarkdownReportGenerator()
        console.print(gen.generate(analysis))


if __name__ == "__main__":
    app()
