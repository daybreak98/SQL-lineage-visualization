"""P0 Golden Case regression runner.

Run with:
    python -m pytest tests/golden_runner.py

The runner exercises the current P0 AnalysisOrchestrator directly against the
golden metadata fixture. Dynamic fields such as analysis_id and elapsed_ms are
not asserted; stable contract fields, diagnostics, lineage nodes/edges and
graph snapshots are.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.domain.contracts import (  # noqa: E402
    AnalyzeSqlRequest,
    DiagnosticCode,
    ImportMode,
    MetadataImportPayload,
    MetadataImportRequest,
)
from app.repositories.metadata_repository import MetadataRepository  # noqa: E402
from app.services.analysis_orchestrator import AnalysisOrchestrator  # noqa: E402
from app.services.metadata_import_service import MetadataImportService  # noqa: E402


FIXTURE = ROOT / "tests" / "golden_cases" / "fixtures" / "p0_metadata_fixture.json"
P0_DIR = ROOT / "tests" / "golden_cases" / "p0"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sql(case_name: str) -> str:
    return (P0_DIR / case_name / "input.sql").read_text(encoding="utf-8")


def _seeded_repo() -> MetadataRepository:
    repo = MetadataRepository(":memory:")
    payload = MetadataImportPayload(**_read_json(FIXTURE))
    result = MetadataImportService(repo).commit(payload)
    assert result.status.value == "committed"
    return repo


def _analyze(case_name: str):
    repo = _seeded_repo()
    metadata = _read_json(P0_DIR / case_name / "metadata.json")
    request = AnalyzeSqlRequest(
        sql=_read_sql(case_name),
        dialect="spark",
        metadata_version=metadata.get("metadata_version", "p0-fixture-v1"),
    )
    return AnalysisOrchestrator(repo).analyze(request)


def _node_ids(result) -> set[str]:
    return {node.id for node in result.lineage_ir.nodes}


def _edge_tuples(result) -> set[tuple[str, str, str]]:
    return {
        (edge.edge_type.value, edge.source, edge.target)
        for edge in result.lineage_ir.edges
    }


def _diagnostic_codes(result) -> set[str]:
    return {diagnostic.code.value for diagnostic in result.diagnostics_report.diagnostics}


def test_gc_p0_001_simple_select():
    result = _analyze("simple_select")
    assert result.status.value == "success"
    assert result.summary.table_count == 1
    assert result.summary.source_column_count == 2
    assert result.summary.output_column_count == 2
    assert result.diagnostics_report.error_count == 0
    assert {
        "column:default.default.order_table.order_no",
        "column:default.default.order_table.user_id",
        "output_column:scope:root:1:order_no",
        "output_column:scope:root:2:user_id",
    }.issubset(_node_ids(result))
    assert (
        "projection",
        "column:default.default.order_table.order_no",
        "output_column:scope:root:1:order_no",
    ) in _edge_tuples(result)
    assert (
        "projection",
        "column:default.default.order_table.user_id",
        "output_column:scope:root:2:user_id",
    ) in _edge_tuples(result)


def test_gc_p0_002_single_table_alias():
    result = _analyze("single_table_alias")
    assert result.status.value == "success"
    assert result.diagnostics_report.error_count == 0
    assert {
        "column:default.default.order_table.order_no",
        "output_column:scope:root:1:order_id",
    }.issubset(_node_ids(result))
    assert (
        "alias",
        "column:default.default.order_table.order_no",
        "output_column:scope:root:1:order_id",
    ) in _edge_tuples(result)


def test_gc_p0_003_unknown_table():
    result = _analyze("unknown_table")
    assert result.status.value == "failed"
    assert result.summary.output_column_count == 0
    assert result.summary.lineage_edge_count == 0
    assert result.metadata_context.missing_tables[0].table == "missing_table"
    assert _diagnostic_codes(result) == {"UNKNOWN_TABLE"}
    skipped = {
        stage.stage: stage.status.value
        for stage in result.stage_statuses
        if stage.stage in {"projection", "lineage", "graph"}
    }
    assert skipped == {
        "projection": "skipped",
        "lineage": "skipped",
        "graph": "skipped",
    }


def test_gc_p0_004_unknown_column():
    result = _analyze("unknown_column")
    assert result.status.value == "partial"
    assert "UNKNOWN_COLUMN" in _diagnostic_codes(result)
    assert result.metadata_context.missing_columns[0].column == "missing_col"
    assert {
        "column:default.default.order_table.order_no",
        "output_column:scope:root:1:order_no",
        "unknown:scope:root:2:missing_col",
        "output_column:scope:root:2:missing_col",
    }.issubset(_node_ids(result))
    assert (
        "unknown",
        "unknown:scope:root:2:missing_col",
        "output_column:scope:root:2:missing_col",
    ) in _edge_tuples(result)


def test_gc_p0_005_ambiguous_column():
    result = _analyze("ambiguous_column")
    assert result.status.value == "partial"
    assert "AMBIGUOUS_COLUMN" in _diagnostic_codes(result)
    ambiguous = result.metadata_context.ambiguous_columns[0]
    assert ambiguous.column == "user_id"
    assert set(ambiguous.candidate_columns) == {
        "column:default.default.order_table.user_id",
        "column:default.default.user_table.user_id",
    }
    assert "unknown:scope:root:1:user_id" in _node_ids(result)


def test_gc_p0_006_simple_expression_direct_dependency():
    result = _analyze("simple_expression")
    assert result.status.value == "success"
    assert result.diagnostics_report.error_count == 0
    assert {
        "column:default.default.order_table.order_amt",
        "output_column:scope:root:1:commission",
    }.issubset(_node_ids(result))
    assert (
        "alias",
        "column:default.default.order_table.order_amt",
        "output_column:scope:root:1:commission",
    ) in _edge_tuples(result)


def test_gc_p0_007_source_location_basic():
    result = _analyze("simple_select")
    assert result.source_locations
    exact_locations = [loc for loc in result.source_locations if loc.range_type == "exact"]
    assert exact_locations
    assert all(loc.source_sql_id for loc in exact_locations)
    assert all(loc.start_line is not None and loc.start_col is not None for loc in exact_locations)


def test_gc_p0_008_graph_view_model_snapshot():
    result = _analyze("simple_select")
    graph = result.graph_view_model
    assert graph.view_mode.value == "column"
    assert {node.node_type.value for node in graph.nodes} >= {"table", "column", "output_column"}
    assert [(edge.edge_type.value, edge.source, edge.target) for edge in graph.edges] == [
        (
            "projection",
            "column:default.default.order_table.order_no",
            "output_column:scope:root:1:order_no",
        ),
        (
            "projection",
            "column:default.default.order_table.user_id",
            "output_column:scope:root:2:user_id",
        ),
    ]
    assert not any("selected" in key.lower() for node in graph.nodes for key in node.data.keys())


def test_gc_p0_009_contract_schema_basic():
    result = _analyze("simple_select")
    payload = result.model_dump(mode="json")
    for key in [
        "schema_version",
        "analysis_id",
        "status",
        "confidence_level",
        "stage_statuses",
        "metadata_context",
        "lineage_ir",
        "diagnostics_report",
        "graph_view_model",
        "source_locations",
        "summary",
        "elapsed_ms",
    ]:
        assert key in payload
    assert "tables_extracted" not in payload
    assert "columns_extracted" not in payload


def test_gc_p0_010_metadata_json_import_preview():
    data = _read_json(P0_DIR / "metadata_json_import" / "input.json")
    repo = MetadataRepository(":memory:")
    result = MetadataImportService(repo).preview(MetadataImportPayload(**data))
    assert result.status.value == "preview_ready"
    assert result.metadata_version == data["metadata_version"]
    assert result.summary["tables"] == len(data["tables"])


def test_gc_p0_011_metadata_json_import_duplicate_column():
    data = _read_json(P0_DIR / "metadata_json_import" / "duplicate_column_input.json")
    repo = MetadataRepository(":memory:")
    result = MetadataImportService(repo).preview(MetadataImportPayload(**data))
    assert DiagnosticCode.METADATA_IMPORT_DUPLICATE_COLUMN in {
        diagnostic.code for diagnostic in result.diagnostics
    }


def test_gc_p0_012_metadata_json_import_request_contract():
    data = _read_json(P0_DIR / "metadata_json_import" / "input.json")
    request = MetadataImportRequest(mode=ImportMode.preview, payload=MetadataImportPayload(**data))
    assert request.mode == ImportMode.preview
    assert request.payload.tables
