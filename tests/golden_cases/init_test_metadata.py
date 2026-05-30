#!/usr/bin/env python3
"""
Golden Case 元数据初始化脚本

将 p0_metadata_fixture.json 导入到 SQLite 元数据仓库中，供 P0 Golden Case 测试使用。

用法:
    # 导入到默认数据库路径
    python init_test_metadata.py

    # 指定数据库路径
    python init_test_metadata.py --db-path /path/to/metadata.db

    # 仅预览（不实际导入）
    python init_test_metadata.py --preview

约定:
    - fixture 文件位于 tests/golden_cases/fixtures/p0_metadata_fixture.json
    - db-path 默认值为 backend/data/lineage_metadata.db
    - 若 backend 不可用，使用 sqlite3 直接导入
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

# ── 项目根目录 ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_PATH = (
    PROJECT_ROOT / "tests" / "golden_cases" / "fixtures" / "p0_metadata_fixture.json"
)
DEFAULT_DB_PATH = PROJECT_ROOT / "backend" / "data" / "lineage_metadata.db"


def load_fixture() -> dict[str, Any]:
    """加载元数据 fixture JSON。"""
    if not FIXTURE_PATH.exists():
        print(f"[ERROR] fixture 文件不存在: {FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_fixture(fixture: dict[str, Any]) -> list[str]:
    """校验 fixture JSON 结构合法性，返回错误列表。"""
    errors: list[str] = []

    if fixture.get("schema_version") != "1.0":
        errors.append("schema_version 必须为 '1.0'")

    if not fixture.get("metadata_version"):
        errors.append("metadata_version 不能为空")

    tables = fixture.get("tables", [])
    if not tables:
        errors.append("tables 列表不能为空")

    for idx, table in enumerate(tables):
        if not table.get("name"):
            errors.append(f"tables[{idx}].name 不能为空")
        columns = table.get("columns", [])
        if not columns:
            errors.append(f"tables[{idx}]({table.get('name', '?')}): columns 不能为空")
        col_names: set[str] = set()
        for cidx, col in enumerate(columns):
            name = col.get("name", "")
            if not name:
                errors.append(
                    f"tables[{idx}]({table.get('name')}).columns[{cidx}].name 不能为空"
                )
            elif name in col_names:
                errors.append(
                    f"tables[{idx}]({table.get('name')}): 字段名 '{name}' 重复"
                )
            col_names.add(name)

    return errors


def import_via_sqlite3(
    fixture: dict[str, Any], db_path: str, preview: bool = False
) -> dict[str, Any]:
    """使用 sqlite3 直接导入元数据到 SQLite。

    创建与 MetadataRepository 兼容的表结构：
      - metadata_versions
      - catalog_tables
      - catalog_columns

    返回 summary 信息。
    """
    metadata_version = fixture["metadata_version"]
    case_sensitive = fixture.get("case_sensitive", False)
    default_catalog = fixture.get("default_catalog", "default")
    default_schema = fixture.get("default_schema", "default")
    tables = fixture["tables"]

    if preview:
        print("[PREVIEW] 元数据导入预览模式，不执行实际写入")
        print(f"  元数据版本: {metadata_version}")
        print(f"  表数量: {len(tables)}")
        total_columns = sum(len(t.get("columns", [])) for t in tables)
        print(f"  字段数量: {total_columns}")
        for t in tables:
            print(f"    表: {t['catalog']}.{t['schema']}.{t['name']}")
            for c in t.get("columns", []):
                print(f"      字段: {c['name']} ({c['data_type']}) [{c.get('comment', '')}]")
        return {
            "mode": "preview",
            "metadata_version": metadata_version,
            "tables_added": len(tables),
            "columns_added": total_columns,
            "errors": 0,
        }

    # 确保数据库目录存在
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        # ── 创建元数据仓库表 ──────────────────────────────────
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata_versions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                version     TEXT    NOT NULL UNIQUE,
                case_sensitive INTEGER NOT NULL DEFAULT 0,
                default_catalog TEXT NOT NULL DEFAULT 'default',
                default_schema  TEXT NOT NULL DEFAULT 'default',
                source_name     TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS catalog_tables (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id   TEXT    NOT NULL UNIQUE,
                catalog     TEXT    NOT NULL DEFAULT 'default',
                schema_name TEXT    NOT NULL DEFAULT 'default',
                table_name  TEXT    NOT NULL,
                comment     TEXT,
                table_type  TEXT    NOT NULL DEFAULT 'table',
                metadata_version_id INTEGER NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (metadata_version_id) REFERENCES metadata_versions(id),
                UNIQUE (metadata_version_id, catalog, schema_name, table_name)
            );

            CREATE TABLE IF NOT EXISTS catalog_columns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id   TEXT    NOT NULL UNIQUE,
                catalog     TEXT    NOT NULL DEFAULT 'default',
                schema_name TEXT    NOT NULL DEFAULT 'default',
                table_name  TEXT    NOT NULL,
                column_name TEXT    NOT NULL,
                data_type   TEXT    NOT NULL DEFAULT 'unknown',
                comment     TEXT,
                ordinal     INTEGER,
                is_partition INTEGER NOT NULL DEFAULT 0,
                nullable    INTEGER,
                metadata_version_id INTEGER NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (metadata_version_id) REFERENCES metadata_versions(id),
                UNIQUE (metadata_version_id, catalog, schema_name, table_name, column_name)
            );

            CREATE INDEX IF NOT EXISTS idx_ct_version
                ON catalog_tables(metadata_version_id);
            CREATE INDEX IF NOT EXISTS idx_cc_version
                ON catalog_columns(metadata_version_id);
            CREATE INDEX IF NOT EXISTS idx_cc_table
                ON catalog_columns(metadata_version_id, catalog, schema_name, table_name);
            """
        )

        # ── 插入 metadata_version ─────────────────────────────
        conn.execute(
            "INSERT OR REPLACE INTO metadata_versions (version, case_sensitive, default_catalog, default_schema, source_name) VALUES (?, ?, ?, ?, ?)",
            (metadata_version, int(case_sensitive), default_catalog, default_schema, fixture.get("source_name")),
        )
        version_row = conn.execute(
            "SELECT id FROM metadata_versions WHERE version = ?",
            (metadata_version,),
        ).fetchone()
        assert version_row is not None, "metadata_version 插入失败"
        version_id = version_row[0]

        # ── 插入表和字段 ───────────────────────────────────────
        tables_added = 0
        columns_added = 0

        for table in tables:
            catalog = table.get("catalog", default_catalog)
            schema = table.get("schema", default_schema)
            name = table.get("name")
            if not name:
                continue

            entity_id = f"table:{catalog}.{schema}.{name}"

            conn.execute(
                """INSERT OR REPLACE INTO catalog_tables
                   (entity_id, catalog, schema_name, table_name, comment, table_type, metadata_version_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (entity_id, catalog, schema, name, table.get("comment"), table.get("table_type", "table"), version_id),
            )
            tables_added += 1

            for col in table.get("columns", []):
                col_name = col.get("name")
                if not col_name:
                    continue

                col_entity_id = f"column:{catalog}.{schema}.{name}.{col_name}"

                conn.execute(
                    """INSERT OR REPLACE INTO catalog_columns
                       (entity_id, catalog, schema_name, table_name, column_name,
                        data_type, comment, ordinal, is_partition, nullable, metadata_version_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        col_entity_id,
                        catalog,
                        schema,
                        name,
                        col_name,
                        col.get("data_type", "unknown"),
                        col.get("comment"),
                        col.get("ordinal"),
                        int(col.get("is_partition", False)),
                        int(col.get("nullable", True)) if col.get("nullable") is not None else None,
                        version_id,
                    ),
                )
                columns_added += 1

        conn.commit()

        return {
            "mode": "commit",
            "metadata_version": metadata_version,
            "tables_added": tables_added,
            "columns_added": columns_added,
            "errors": 0,
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def try_import_via_backend(
    fixture: dict[str, Any], db_path: str, preview: bool = False
) -> bool:
    """尝试通过后端 MetadataRepository 导入。

    Returns:
        True 如果后端模块可用且导入成功，否则 False。
    """
    try:
        # 将项目根目录加入 sys.path
        backend_root = str(PROJECT_ROOT / "backend")
        if backend_root not in sys.path:
            sys.path.insert(0, backend_root)

        from app.repositories.metadata_repository import (  # type: ignore[import-untyped]
            MetadataRepository,
        )

        repo = MetadataRepository(db_path=db_path)
        repo.initialize_schema()

        if preview:
            print("[PREVIEW via MetadataRepository]")
            # 只做校验，不做写入
            tables = fixture["tables"]
            for t in tables:
                col_names = [c["name"] for c in t.get("columns", [])]
                print(f"  表: {t.get('catalog', 'default')}.{t.get('schema', 'default')}.{t['name']} (字段: {col_names})")
            return True

        # 实际导入
        metadata_version = fixture["metadata_version"]
        case_sensitive = fixture.get("case_sensitive", False)
        default_catalog = fixture.get("default_catalog", "default")
        default_schema = fixture.get("default_schema", "default")

        repo.create_metadata_version(
            version=metadata_version,
            case_sensitive=case_sensitive,
            default_catalog=default_catalog,
            default_schema=default_schema,
            source_name=fixture.get("source_name"),
        )

        for table in fixture["tables"]:
            catalog = table.get("catalog", default_catalog)
            schema = table.get("schema", default_schema)
            name = table["name"]
            repo.upsert_table(
                metadata_version=metadata_version,
                catalog=catalog,
                schema=schema,
                table_name=name,
                comment=table.get("comment"),
                table_type=table.get("table_type", "table"),
            )
            for col in table.get("columns", []):
                repo.upsert_column(
                    metadata_version=metadata_version,
                    catalog=catalog,
                    schema=schema,
                    table_name=name,
                    column_name=col["name"],
                    data_type=col.get("data_type", "unknown"),
                    comment=col.get("comment"),
                    ordinal=col.get("ordinal"),
                    is_partition=col.get("is_partition", False),
                    nullable=col.get("nullable"),
                )

        print("[OK] 通过 MetadataRepository 导入成功")
        return True

    except ImportError:
        return False
    except Exception as e:
        print(f"[WARN] MetadataRepository 导入异常: {e}", file=sys.stderr)
        print("[INFO] 回退到 sqlite3 直接导入模式", file=sys.stderr)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 p0_metadata_fixture.json 导入到 SQLite 元数据仓库"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite 数据库路径 (默认: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="仅预览，不实际导入",
    )
    parser.add_argument(
        "--force-sqlite3",
        action="store_true",
        help="强制使用 sqlite3 直接导入，跳过 MetadataRepository 检测",
    )
    args = parser.parse_args()

    # ── 加载 fixture ───────────────────────────────────────────
    print(f"[INFO] 加载 fixture: {FIXTURE_PATH}")
    fixture = load_fixture()
    print(f"  元数据版本: {fixture['metadata_version']}")
    print(f"  表数量: {len(fixture['tables'])}")

    # ── 校验 fixture ───────────────────────────────────────────
    errors = validate_fixture(fixture)
    if errors:
        print("[ERROR] fixture 校验失败:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("[OK] fixture 校验通过")

    # ── 导入 ───────────────────────────────────────────────────
    if args.preview:
        import_via_sqlite3(fixture, args.db_path, preview=True)
        print("\n[DONE] 预览完成（未实际导入）")
        return

    db_path = args.db_path
    summary: dict[str, Any]

    # 优先尝试后端 MetadataRepository
    if not args.force_sqlite3 and try_import_via_backend(fixture, db_path, preview=False):
        return

    # 回退到 sqlite3 直接导入
    print("[INFO] 使用 sqlite3 直接导入模式")
    summary = import_via_sqlite3(fixture, db_path, preview=False)

    print(f"\n[DONE] 导入完成")
    print(f"  数据库路径: {db_path}")
    print(f"  元数据版本: {summary['metadata_version']}")
    print(f"  表新增: {summary['tables_added']}")
    print(f"  字段新增: {summary['columns_added']}")
    print(f"  错误数: {summary['errors']}")


if __name__ == "__main__":
    main()
