"""
conftest.py - R00 + R01 测试 fixtures

提供可复用的测试 fixtures：
- temp_db: 创建临时 SQLite 数据库，自动清理
- repo_with_fixture: 加载 golden case fixture 数据的 repository
"""

import json
import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# 路径工具：相对于 conftest.py 定位项目根
# ---------------------------------------------------------------------------
def _project_root() -> str:
    """返回项目根目录（backend/tests/conftest.py → 项目根）。"""
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )


def _fixture_path(filename: str) -> str:
    """返回 golden fixtures 目录下文件的绝对路径。"""
    return os.path.join(
        _project_root(),
        "tests",
        "golden_cases",
        "fixtures",
        filename,
    )


# ---------------------------------------------------------------------------
# Global fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def temp_db():
    """
    创建临时 SQLite 数据库用于隔离测试。

    每次测试获得独立的数据库文件，测试结束后自动清理。
    返回 (MetadataRepository, db_path)。
    """
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    try:
        from app.repositories.metadata_repository import MetadataRepository
        repo = MetadataRepository(db_path)
        yield repo, db_path
    finally:
        os.close(db_fd)
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture(scope="function")
def repo_with_fixture(temp_db):
    """
    加载 p0-fixture-v1 golden case 元数据的 repository。

    返回 (MetadataRepository, db_path)。

    如果 fixture JSON 文件不存在（后端代码尚未创建），
    返回空的 repository（不抛异常，便于测试框架配置本身可用）。
    """
    repo, db_path = temp_db
    fixture_file = _fixture_path("p0_metadata_fixture.json")

    if not os.path.exists(fixture_file):
        # fixture 文件尚未创建（后端开发早期阶段）
        # 返回空的 repo，由各测试自行判断
        return repo, db_path

    with open(fixture_file, encoding="utf-8") as f:
        data = json.load(f)

    # 创建元数据版本
    repo.create_metadata_version(
        data["metadata_version"],
        data.get("source_name"),
    )

    # 导入所有表
    for table in data["tables"]:
        normalized_name = (
            table["name"] if data["case_sensitive"]
            else table["name"].lower()
        )
        table_id = repo.upsert_table(
            data["metadata_version"],
            table["catalog"],
            table["schema"],
            table["name"],
            normalized_name,
            table.get("comment"),
        )

        # 准备列数据（注意：MetadataRepository 使用 column_name / normalized_column_name）
        columns = []
        for col in table["columns"]:
            normalized_col = (
                col["name"] if data["case_sensitive"]
                else col["name"].lower()
            )
            columns.append({
                "column_name": col["name"],
                "normalized_column_name": normalized_col,
                "data_type": col.get("data_type", "unknown"),
                "comment": col.get("comment"),
                "ordinal": col.get("ordinal"),
                "is_partition": col.get("is_partition", False),
            })

        # 批量 upsert 列
        repo.upsert_columns(table_id, data["metadata_version"], columns)

    return repo, db_path
