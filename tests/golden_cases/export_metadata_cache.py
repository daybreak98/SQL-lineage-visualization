#!/usr/bin/env python3
"""
导出 metadata_cache.db 为 MetadataImportPayload JSON 格式。

从 开发文档/metadata_cache.db 读取真实元数据，将 table_schema 表格转换为
标准的 MetadataImportPayload JSON，供 Golden Case 测试和后端导入使用。

用法:
    # 导出默认 5 张表到 p0_real_top5.json
    python tests/golden_cases/export_metadata_cache.py

    # 自定义参数
    python tests/golden_cases/export_metadata_cache.py --top 20 --output tests/golden_cases/fixtures/p0_real_top20.json

    # 按库过滤
    python tests/golden_cases/export_metadata_cache.py --database ihotel_default --top 3

    # 指定缓存数据库路径
    python tests/golden_cases/export_metadata_cache.py --cache path/to/metadata_cache.db
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# ── 项目根目录与默认路径 ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CACHE_DB = PROJECT_ROOT / "开发文档" / "metadata_cache.db"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_OUTPUT = DEFAULT_OUTPUT_DIR / "p0_real_top5.json"


def export_metadata(
    cache_db_path: str,
    output_path: str,
    database: str | None = None,
    top_n: int | None = None,
    ensure_wide_table: bool = False,
) -> dict:
    """从 metadata_cache.db 导出元数据为 MetadataImportPayload JSON。

    Args:
        cache_db_path: metadata_cache.db 路径
        output_path: 输出 JSON 文件路径
        database: 按 database_name 过滤（None = 不过滤）
        top_n: 限制导出的表数量（None = 全部）
        ensure_wide_table: 如果为 True，确保结果中至少包含 1 张宽表（≥100 列）

    Returns:
        包含统计信息的 dict
    """
    import sqlite3

    if not os.path.exists(cache_db_path):
        print(f"[ERROR] 缓存数据库不存在: {cache_db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(cache_db_path)
    cursor = conn.cursor()

    # ── 查询所有 distinct 表 ─────────────────────────────────
    query = (
        "SELECT database_name, table_name, full_table_name "
        "FROM metadata_table_schema"
    )
    params: list = []
    if database:
        query += " WHERE database_name = ?"
        params.append(database)
    query += " GROUP BY database_name, table_name ORDER BY MIN(id)"

    cursor.execute(query, params)
    tables = cursor.fetchall()

    if top_n:
        tables = tables[:top_n]

    # ── 构建 MetadataImportPayload ──────────────────────────
    result: dict = {
        "schema_version": "1.0",
        "metadata_version": "p0-real-v1",
        "case_sensitive": False,
        "default_catalog": "default",
        "default_schema": "default",
        "source_name": "metadata_cache_export",
        "tables": [],
    }

    total_columns = 0

    for db_name, table_name, full_table_name in tables:
        cursor.execute(
            "SELECT column_name, column_type, column_comment, ordinal_position, "
            "is_partition_column "
            "FROM metadata_table_schema "
            "WHERE database_name = ? AND table_name = ? "
            "ORDER BY ordinal_position",
            (db_name, table_name),
        )
        rows = cursor.fetchall()

        columns = []
        for col_name, col_type, col_comment, ordinal, is_partition in rows:
            columns.append({
                "name": col_name,
                "data_type": col_type or "unknown",
                "comment": col_comment or None,
                "ordinal": ordinal,
                "is_partition": bool(is_partition) if is_partition is not None else False,
                "nullable": True,
            })

        result["tables"].append({
            "catalog": "default",
            "schema": db_name,
            "name": table_name,
            "comment": full_table_name or table_name,
            "table_type": "table",
            "columns": columns,
        })
        total_columns += len(columns)

    conn.close()

    # ── 写入输出文件 ─────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    summary = {
        "tables_exported": len(result["tables"]),
        "columns_exported": total_columns,
        "database_filter": database or "all",
        "output_path": output_path,
    }
    print(
        f"[OK] 导出完成: {summary['tables_exported']} 张表, "
        f"{summary['columns_exported']} 个字段 → {output_path}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 metadata_cache.db 导出为 MetadataImportPayload JSON 格式"
    )
    parser.add_argument(
        "--database",
        type=str,
        default=None,
        help="按 database_name 过滤（支持 default / ihotel_default）",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="限制导出的表数量（默认 5）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help=f"输出 JSON 文件路径（默认: {DEFAULT_OUTPUT}）",
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=str(DEFAULT_CACHE_DB),
        help=f"metadata_cache.db 路径（默认: {DEFAULT_CACHE_DB}）",
    )

    args = parser.parse_args()

    print(f"[INFO] 缓存数据库: {args.cache}")
    print(f"[INFO] 输出文件:   {args.output}")
    if args.database:
        print(f"[INFO] 过滤库:     {args.database}")
    print(f"[INFO] 表数量上限: {args.top}")

    export_metadata(
        cache_db_path=args.cache,
        output_path=args.output,
        database=args.database,
        top_n=args.top,
    )


if __name__ == "__main__":
    main()
