import os
import tempfile

from fastapi.testclient import TestClient

from app.domain.contracts import MetadataColumnInput, MetadataImportPayload, MetadataTableInput
from app.main import app
from app.repositories.metadata_repository import MetadataRepository
from app.services.metadata_import_service import MetadataImportService


def _seed_db(db_path: str) -> None:
    repo = MetadataRepository(db_path)
    payload = MetadataImportPayload(
        metadata_version="api-v1",
        tables=[
            MetadataTableInput(
                name="order_table",
                columns=[
                    MetadataColumnInput(name="order_no", data_type="string", ordinal=1),
                    MetadataColumnInput(name="user_id", data_type="bigint", ordinal=2),
                ],
            ),
            MetadataTableInput(
                name="user_table",
                columns=[
                    MetadataColumnInput(name="user_id", data_type="bigint", ordinal=1),
                    MetadataColumnInput(name="user_name", data_type="string", ordinal=2),
                ],
            ),
        ],
    )
    result = MetadataImportService(repo).commit(payload)
    assert result.status.value == "committed"
    repo.close()


def _client_with_seeded_db(monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    _seed_db(db_path)
    monkeypatch.setenv("LINEAGE_DB_PATH", db_path)
    return TestClient(app), db_path


def test_analyze_api_returns_analysis_result_contract(monkeypatch):
    client, db_path = _client_with_seeded_db(monkeypatch)
    try:
        response = client.post(
            "/api/sql/analyze",
            json={
                "sql": "SELECT o.order_no, u.user_name FROM order_table o JOIN user_table u ON o.user_id = u.user_id",
                "dialect": "spark",
                "metadata_version": "api-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["schema_version"] == "1.0"
        assert data["status"] == "success"
        assert "tables_extracted" not in data
        assert data["summary"]["source_column_count"] == 2
        assert data["summary"]["output_column_count"] == 2
        assert data["graph_view_model"]["nodes"]
        assert data["graph_view_model"]["edges"]
        assert any(s["stage"] == "semantics" and s["status"] == "skipped" for s in data["stage_statuses"])
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_analyze_api_unknown_column_is_partial(monkeypatch):
    client, db_path = _client_with_seeded_db(monkeypatch)
    try:
        response = client.post(
            "/api/sql/analyze",
            json={
                "sql": "SELECT o.missing_col FROM order_table o",
                "dialect": "spark",
                "metadata_version": "api-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial"
        codes = [d["code"] for d in data["diagnostics_report"]["diagnostics"]]
        assert "UNKNOWN_COLUMN" in codes
        assert any(n["node_type"] == "unknown" for n in data["lineage_ir"]["nodes"])
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass


def test_analyze_api_parse_error_is_failed(monkeypatch):
    client, db_path = _client_with_seeded_db(monkeypatch)
    try:
        response = client.post(
            "/api/sql/analyze",
            json={
                "sql": "SELEC a FRM t",
                "dialect": "spark",
                "metadata_version": "api-v1",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["diagnostics_report"]["error_count"] >= 1
        assert all(
            s["status"] == "skipped"
            for s in data["stage_statuses"]
            if s["stage"] in {"scope", "name_resolution", "projection", "lineage", "graph"}
        )
    finally:
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except PermissionError:
                pass
