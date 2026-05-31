"""
conftest.py - R00 + R01 + R02 测试 fixtures

提供可复用的测试 fixtures：
- temp_db: 创建临时 SQLite 数据库，自动清理
- repo_with_fixture: 加载 golden case fixture 数据的 repository
- repo: R02 集成测试使用的独立内存 SQLite repository
- valid_payload: R02 JSON 元数据导入的最小合法 payload
- large_payload: R02 多表多字段的合法 payload
- import_service: R02 绑定临时数据库的 MetadataImportService 实例
"""

import json
import os
import tempfile
from typing import Any

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


# ---------------------------------------------------------------------------
# R01: MetadataStore integration tests fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def repo():
    """Create a repository backed by an in-memory SQLite database."""
    from app.repositories.metadata_repository import MetadataRepository
    r = MetadataRepository(db_path=":memory:")
    yield r


# ---------------------------------------------------------------------------
# R02: JSON 元数据导入 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def valid_payload() -> Any:
    """构造一个最小合法 MetadataImportPayload（R02）。

    包含 1 张表、2 个字段，覆盖正常导入场景。
    返回 MetadataImportPayload 实例。
    """
    from app.domain.contracts import (
        MetadataColumnInput,
        MetadataImportPayload,
        MetadataTableInput,
    )
    return MetadataImportPayload(
        schema_version="1.0",
        metadata_version="test-v1",
        case_sensitive=False,
        default_catalog="default",
        default_schema="default",
        source_name="r02-test",
        tables=[
            MetadataTableInput(
                catalog="default",
                schema="default",
                name="test_table",
                comment="测试表",
                table_type="table",
                columns=[
                    MetadataColumnInput(
                        name="col_a",
                        data_type="string",
                        comment="字段A",
                        ordinal=1,
                        is_partition=False,
                        nullable=False,
                    ),
                    MetadataColumnInput(
                        name="col_b",
                        data_type="int",
                        comment="字段B",
                        ordinal=2,
                        is_partition=False,
                        nullable=True,
                    ),
                ],
            ),
        ],
    )


@pytest.fixture(scope="function")
def large_payload() -> Any:
    """构造包含多表多字段的较大合法 Payload（R02）。

    包含 3 张表、每表 5 个字段，用于 multi-table 导入测试。
    返回 MetadataImportPayload 实例。
    """
    from app.domain.contracts import (
        MetadataColumnInput,
        MetadataImportPayload,
        MetadataTableInput,
    )
    tables = []
    for ti in range(3):
        columns = []
        for ci in range(5):
            columns.append(
                MetadataColumnInput(
                    name=f"col_{ti}_{ci}",
                    data_type="string" if ci % 2 == 0 else "int",
                    ordinal=ci + 1,
                )
            )
        tables.append(
            MetadataTableInput(
                catalog="default",
                schema="default",
                name=f"multi_table_{ti}",
                columns=columns,
            )
        )
    return MetadataImportPayload(
        metadata_version="test-multi-v1",
        tables=tables,
    )


@pytest.fixture(scope="function")
def import_service(temp_db: Any) -> Any:
    """创建一个绑定临时数据库的 MetadataImportService 实例（R02）。

    如果 MetadataImportService 尚未实现（ImportError），返回 None，
    测试应使用 pytest.skip 跳过。
    """
    try:
        from app.services.metadata_import_service import MetadataImportService
        repo, _ = temp_db
        return MetadataImportService(repo)
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# R02 辅助断言工具（计划由 test-engineer 按需扩展）
# ---------------------------------------------------------------------------

def diagnostics_by_code(result: Any, code: Any) -> list:
    """从 MetadataImportResult 中按 DiagnosticCode 过滤 diagnostics。"""
    return [d for d in result.diagnostics if d.code == code]


def diagnostics_by_level(result: Any, level: Any) -> list:
    """从 MetadataImportResult 中按 DiagnosticLevel 过滤 diagnostics。"""
    return [d for d in result.diagnostics if d.level == level]
