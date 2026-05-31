"""M21 精简 Golden Case：Completion 表名补全 API 测试。"""

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
        "tests", "golden_cases", "p1", "completion_basic", name,
    )


def _seed_completion_db(db_path: str) -> None:
    """Seed DB with completion test metadata."""
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
    _seed_completion_db(db_path)
    monkeypatch.setenv("LINEAGE_DB_PATH", db_path)
    return TestClient(app), db_path


# ── Tests ────────────────────────────────────────────────────

def test_completion_returns_table_candidates_from_fixture(monkeypatch):
    """光标在 FROM 后应返回表名补全候选。"""
    client, db_path = _client_with_db(monkeypatch, "comp1")
    try:
        # SQL: SELECT * FROM [cursor here]
        sql = "SELECT * FROM "
        response = client.post(
            "/api/editor/completion",
            json={
                "sql": sql,
                "cursor_line": 1,
                "cursor_col": len(sql) + 1,
                "dialect": "spark",
                "metadata_version": "completion-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        table_candidates = [c for c in data["candidates"] if c["type"] == "table"]
        # 应包含 users / orders / products
        table_texts = {c["text"] for c in table_candidates}
        assert "users" in table_texts
        assert "orders" in table_texts
        assert "products" in table_texts
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_completion_returns_keyword_candidates(monkeypatch):
    """空 SQL 应返回关键字补全。"""
    client, db_path = _client_with_db(monkeypatch, "comp2")
    try:
        response = client.post(
            "/api/editor/completion",
            json={
                "sql": "",
                "cursor_line": 1,
                "cursor_col": 1,
                "dialect": "spark",
                "metadata_version": "latest",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        # 至少应有 SELECT 关键字
        texts = {c["text"] for c in data["candidates"]}
        assert "SELECT" in texts
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_completion_returns_select_keyword_for_se_prefix(monkeypatch):
    """Typing `se` should expose SELECT as a keyword candidate."""
    client, db_path = _client_with_db(monkeypatch, "comp2-se")
    try:
        response = client.post(
            "/api/editor/completion",
            json={
                "sql": "se",
                "cursor_line": 1,
                "cursor_col": 3,
                "dialect": "spark",
                "metadata_version": "latest",
            },
        )
        assert response.status_code == 200
        data = response.json()
        select_candidates = [
            c for c in data["candidates"]
            if c["text"] == "SELECT" and c["type"] == "keyword"
        ]
        assert select_candidates
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_completion_returns_column_candidates(monkeypatch):
    """光标在 SELECT 后应返回字段补全候选。"""
    client, db_path = _client_with_db(monkeypatch, "comp3")
    try:
        # SQL: SELECT [cursor here] FROM users
        sql = "SELECT "
        response = client.post(
            "/api/editor/completion",
            json={
                "sql": sql,
                "cursor_line": 1,
                "cursor_col": len(sql) + 1,
                "dialect": "spark",
                "metadata_version": "completion-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        column_candidates = [c for c in data["candidates"] if c["type"] == "column"]
        # SELECT 后没有 FROM，会返回 keyword + column 混合
        assert len(data["candidates"]) > 0
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_completion_returns_400_for_invalid_input(monkeypatch):
    """缺失必需字段应返回 422。"""
    client, db_path = _client_with_db(monkeypatch, "comp4")
    try:
        response = client.post(
            "/api/editor/completion",
            json={"sql": "SELECT * FROM users"},
        )
        # 缺少 cursor_line / cursor_col 会导致验证错误
        assert response.status_code == 422
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass
