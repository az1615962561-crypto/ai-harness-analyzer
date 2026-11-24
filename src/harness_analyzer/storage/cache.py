"""分析结果缓存模块"""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


class AnalysisCache:
    """分析结果 SQLite 缓存"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "analyses.db"
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库及表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    app_name TEXT PRIMARY KEY,
                    category TEXT,
                    analysis_json TEXT,
                    analyzed_at TEXT
                )
                """
            )
            conn.commit()

    def save(self, app_name: str, category: str, analysis_json: str) -> None:
        """保存分析结果 (INSERT OR REPLACE)"""
        if isinstance(analysis_json, (dict, list)):
            analysis_json_str = json.dumps(analysis_json, ensure_ascii=False)
        else:
            analysis_json_str = str(analysis_json)

        analyzed_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO analyses (app_name, category, analysis_json, analyzed_at)
                VALUES (?, ?, ?, ?)
                """,
                (app_name, category, analysis_json_str, analyzed_at),
            )
            conn.commit()

    def get(self, app_name: str) -> dict | None:
        """获取指定应用的分析结果并解析为字典"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT analysis_json FROM analyses WHERE app_name = ?",
                (app_name,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return json.loads(row[0])

    def list_cached(self) -> list[dict]:
        """列出所有已缓存的应用分析简要信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT app_name, category, analyzed_at FROM analyses ORDER BY analyzed_at DESC"
            )
            rows = cursor.fetchall()
            return [
                {
                    "name": row[0],
                    "app_name": row[0],
                    "category": row[1],
                    "analyzed_at": row[2],
                }
                for row in rows
            ]

    def is_fresh(self, app_name: str, max_age_days: int = 30) -> bool:
        """检查指定应用的分析结果是否在保鲜期内"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT analyzed_at FROM analyses WHERE app_name = ?",
                (app_name,),
            )
            row = cursor.fetchone()
            if row is None:
                return False

            analyzed_at_str = row[0]
            try:
                analyzed_dt = datetime.fromisoformat(analyzed_at_str)
                now = datetime.now(timezone.utc)
                if analyzed_dt.tzinfo is None:
                    analyzed_dt = analyzed_dt.replace(tzinfo=timezone.utc)
                return (now - analyzed_dt) <= timedelta(days=max_age_days)
            except Exception:
                return False

    def clear(self, app_name: str | None = None) -> None:
        """清除指定应用缓存或清空所有缓存"""
        with sqlite3.connect(self.db_path) as conn:
            if app_name is not None:
                conn.execute(
                    "DELETE FROM analyses WHERE app_name = ?",
                    (app_name,),
                )
            else:
                conn.execute("DELETE FROM analyses")
            conn.commit()
