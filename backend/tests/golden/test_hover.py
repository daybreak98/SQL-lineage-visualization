"""M21 精简 Golden Case：Hover 字段信息 API 测试。"""

import json
import os
import tempfile

from fastapi.testclient import TestClient

from app.domain.contracts import MetadataColumnInput, MetadataImportPayload, MetadataTableInput
from app.main import app
from app.repositories.metadata_repository import MetadataRepository
from app.services.metadata_import_service import MetadataImportService


# ── Fixture helpers ──────────────────────────────────────────

def _fixture_path(name: str) -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "tests", "golden_cases", "p1", "hover_basic", name,
    )


def _seed_hover_db(db_path: str) -> None:
    """Seed DB with hover test metadata (users + orders tables)."""
    fixture_file = _fixture_path("metadata.json")
    with open(fixture_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    repo = MetadataRepository(db_path)
    payload = MetadataImportPayload(**data)
    result = MetadataImportService(repo).commit(payload)
    assert result.status.value == "committed"
    repo.close()


def _client_with_db(monkeypatch, db_label: str):
    """Create a TestClient with a temporary seeded DB."""
    fd, db_path = tempfile.mkstemp(suffix=f"-{db_label}.db")
    os.close(fd)
    _seed_hover_db(db_path)
    monkeypatch.setenv("LINEAGE_DB_PATH", db_path)
    return TestClient(app), db_path


# ── SQL 文本 ─────────────────────────────────────────────────

_HOVER_SQL = """SELECT u.id, u.name, o.amount
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.amount > 100"""


def _line_col(sql: str, target: str) -> tuple[int, int]:
    """返回 target 在 sql 中第一次出现的 (line, col)，1-based。"""
    offset = sql.find(target)
    assert offset >= 0, f"target '{target}' not found in SQL"
    prefix = sql[:offset]
    line = prefix.count("\n") + 1
    last_nl = prefix.rfind("\n")
    col = (offset - last_nl) if last_nl >= 0 else (offset + 1)
    return line, col


# ── Tests ────────────────────────────────────────────────────

def test_hover_returns_column_info_from_fixture(monkeypatch):
    """光标在 o.amount 上应返回字段类型和注释。"""
    client, db_path = _client_with_db(monkeypatch, "hover1")
    try:
        line, col = _line_col(_HOVER_SQL, "amount")
        # cursor should be somewhere on the "amount" identifier
        response = client.post(
            "/api/editor/hover",
            json={
                "sql": _HOVER_SQL,
                "cursor_line": line,
                "cursor_col": col + 2,  # inside the identifier
                "dialect": "spark",
                "metadata_version": "hover-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        hover = data.get("hover")
        assert hover is not None, f"No hover returned. data={data}"
        assert hover["type"] == "column"
        assert "amount" in (hover.get("text") or "")
        assert hover.get("data_type") is not None
        assert hover.get("data_type") != "unknown"
        assert hover.get("comment") is not None
        assert hover.get("source") is not None
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_hover_returns_table_info(monkeypatch):
    """光标在 users 表名上应返回表注释。"""
    client, db_path = _client_with_db(monkeypatch, "hover2")
    try:
        line, col = _line_col(_HOVER_SQL, "FROM users")
        # cursor on "users"
        users_col = _HOVER_SQL.find("users")
        prefix = _HOVER_SQL[:users_col]
        uline = prefix.count("\n") + 1
        last_nl = prefix.rfind("\n")
        ucol = (users_col - last_nl) if last_nl >= 0 else (users_col + 1)

        response = client.post(
            "/api/editor/hover",
            json={
                "sql": _HOVER_SQL,
                "cursor_line": uline,
                "cursor_col": ucol + 2,
                "dialect": "spark",
                "metadata_version": "hover-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        hover = data.get("hover")
        assert hover is not None, f"No hover on table users. data={data}"
        assert hover["type"] == "table"
        assert "users" in (hover.get("text") or "").lower()
        # 表注释
        assert hover.get("comment") is not None
        assert "用户" in (hover.get("comment") or "")
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_hover_returns_null_for_unknown_identifier(monkeypatch):
    """光标在不存在的标识符上应返回 null hover。"""
    client, db_path = _client_with_db(monkeypatch, "hover3")
    try:
        response = client.post(
            "/api/editor/hover",
            json={
                "sql": "SELECT nonexistent_col FROM users",
                "cursor_line": 1,
                "cursor_col": 8,  # on 'n' of 'nonexistent_col'
                "dialect": "spark",
                "metadata_version": "hover-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        hover = data.get("hover")
        # 未知字段应返回 null
        assert hover is None
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_hover_returns_400_for_missing_fields(monkeypatch):
    """缺失必需字段应返回 422。"""
    client, db_path = _client_with_db(monkeypatch, "hover4")
    try:
        response = client.post(
            "/api/editor/hover",
            json={"sql": "SELECT 1"},
        )
        assert response.status_code == 422
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass
