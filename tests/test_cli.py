"""Tests for Typer CLI commands."""
from typer.testing import CliRunner
from harness_analyzer.cli import app

runner = CliRunner()


def test_cli_list_and_search():
    res = runner.invoke(app, ["list", "--category", "engineering"])
    assert res.exit_code == 0
    assert "Cursor" in res.stdout

    res_search = runner.invoke(app, ["search", "SQL"])
    assert res_search.exit_code == 0
    assert "ChatBI" in res_search.stdout


def test_cli_info():
    res = runner.invoke(app, ["info", "cursor"])
    assert res.exit_code == 0
    assert "Cursor" in res.stdout
    assert "沙箱隔离模型" in res.stdout


def test_cli_offline_analyze_compare_and_report(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("HARNESS_REPORTS_DIR", str(tmp_path / "reports"))
    # Reset cached singleton settings
    import harness_analyzer.config as cfg
    cfg._settings = None

    res1 = runner.invoke(app, ["analyze", "cursor", "--offline"])
    assert res1.exit_code == 0
    assert (tmp_path / "reports" / "cursor.md").exists()

    res2 = runner.invoke(app, ["analyze", "chatbi", "--offline"])
    assert res2.exit_code == 0
    assert (tmp_path / "reports" / "chatbi.md").exists()

    comp_out = tmp_path / "reports" / "cmp.md"
    res_cmp = runner.invoke(app, ["compare", "Cursor", "ChatBI", "-o", str(comp_out)])
    assert res_cmp.exit_code == 0
    assert comp_out.exists()
    content = comp_out.read_text(encoding="utf-8")
    assert "★★★★★" in content
    assert "应用层：产品方案横向对比" in content

    res_rep = runner.invoke(app, ["report", "cursor"])
    assert res_rep.exit_code == 0
    assert "产品经理产品方案指导" in res_rep.stdout
