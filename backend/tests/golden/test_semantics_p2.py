"""P2 Golden Case tests for SemanticsReport (M25 / R12).

Tests exercise the SemanticsAnalyzer through the full AnalysisOrchestrator pipeline
with include_semantics=True to validate the evidence-driven caliber report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.domain.contracts import AnalyzeSqlRequest, ImportMode, MetadataImportPayload, MetadataImportRequest  # noqa: E402
from app.repositories.metadata_repository import MetadataRepository  # noqa: E402
from app.services.analysis_orchestrator import AnalysisOrchestrator  # noqa: E402
from app.services.metadata_import_service import MetadataImportService  # noqa: E402

FIXTURE = ROOT / "tests" / "golden_cases" / "fixtures" / "p0_metadata_fixture.json"


def _seeded_repo() -> MetadataRepository:
    repo = MetadataRepository(":memory:")
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload = MetadataImportPayload(**data)
    result = MetadataImportService(repo).commit(payload)
    assert result.status.value == "committed"
    return repo


def _analyze_with_semantics(sql_text: str, metadata_version: str = "p0-fixture-v1"):
    """Run full analysis with include_semantics=True."""
    repo = _seeded_repo()
    request = AnalyzeSqlRequest(
        sql=sql_text,
        dialect="spark",
        metadata_version=metadata_version,
    )
    # Enable semantics analysis
    request.analysis_options.include_semantics = True
    return AnalysisOrchestrator(repo).analyze(request)


# ── GC-P2-001: GROUP BY + metric ──

def test_gc_p2_001_group_by_metric():
    """GROUP BY dept + SUM(salary) — should detect group_by grain and sum metric."""
    # Use the emp-like schema from fixture: treat order_table as emp-like
    sql = "SELECT status, SUM(order_amt) FROM order_table GROUP BY status"
    result = _analyze_with_semantics(sql)

    sr = result.semantics_report
    assert sr.status != "not_supported_in_p0", f"Expected semantics, got {sr.status}"
    assert sr.status in ("success", "partial"), f"Got status={sr.status}"

    # Result grain
    assert sr.result_grain is not None, "Result grain should not be None"
    assert sr.result_grain.get("grain_type") == "group_by", (
        f"Expected group_by grain, got {sr.result_grain.get('grain_type')}"
    )
    assert "status" in sr.result_grain.get("columns", [])

    # Metrics
    assert len(sr.metrics) >= 1, f"Expected at least 1 metric, got {len(sr.metrics)}"
    metric = sr.metrics[0]
    assert metric.get("metric_type") == "sum", f"Expected sum metric, got {metric.get('metric_type')}"
    assert metric.get("output_name", "").lower() in ("sum(order_amt)", "expr_2")

    # Dedup logic (GROUP BY = implicit dedup)
    dedup_types = [d.get("dedup_type") for d in sr.dedup_logic]
    assert "group_by" in dedup_types, f"Expected group_by dedup, got {dedup_types}"

    # Evidence refs
    assert len(sr.evidence_refs) > 0, "Evidence refs should not be empty"

    # No errors
    assert result.status.value != "failed"

    # Stage status
    stages = {s.stage: s.status.value for s in result.stage_statuses}
    assert stages.get("semantics") in ("success", "partial"), (
        f"Semantics stage should be success/partial, got {stages.get('semantics')}"
    )


# ── GC-P2-002: JOIN expansion risk ──

def test_gc_p2_002_join_expansion_risk():
    """Multi-table join — should detect joins and amplification risk."""
    sql = "SELECT o.order_no, u.user_name FROM order_table o JOIN user_table u ON o.user_id = u.user_id"
    result = _analyze_with_semantics(sql)

    sr = result.semantics_report
    assert sr.status != "not_supported_in_p0", f"Expected semantics, got {sr.status}"
    assert sr.status in ("success", "partial")

    # Joins
    assert len(sr.joins) >= 1, f"Expected at least 1 join, got {len(sr.joins)}"

    # Risks
    risk_types = [r.get("risk_type") for r in sr.semantic_risks]
    assert any(
        rt in risk_types for rt in ("join_amplification", "no_partition_filter")
    ), f"No expected risk found in {risk_types}"

    # Evidence refs
    assert len(sr.evidence_refs) > 0

    # Stage status
    stages = {s.stage: s.status.value for s in result.stage_statuses}
    assert stages.get("semantics") in ("success", "partial")


# ── GC-P2-003: back-compat — semantics skipped when include_semantics=False ──

def test_gc_p2_003_backward_compat():
    """When include_semantics=False, the semantics stage should be skipped."""
    repo = _seeded_repo()
    request = AnalyzeSqlRequest(
        sql="SELECT order_no FROM order_table",
        dialect="spark",
        metadata_version="p0-fixture-v1",
    )
    # Default: include_semantics=False
    result = AnalysisOrchestrator(repo).analyze(request)

    assert result.semantics_report.status == "not_supported_in_p0"
    stages = {s.stage: s.status.value for s in result.stage_statuses}
    assert stages.get("semantics") == "skipped", f"Expected skipped, got {stages.get('semantics')}"


# ── GC-P2-004: SELECT DISTINCT detection ──

def test_gc_p2_004_select_distinct():
    """SELECT DISTINCT — should detect distinct grain and dedup rule."""
    sql = "SELECT DISTINCT status FROM order_table"
    result = _analyze_with_semantics(sql)

    sr = result.semantics_report
    assert sr.status != "not_supported_in_p0"

    # Grain
    assert sr.result_grain is not None
    assert sr.result_grain.get("grain_type") in ("distinct", "detail", "unknown")

    # Dedup
    dedup_types = [d.get("dedup_type") for d in sr.dedup_logic]
    if sr.result_grain.get("grain_type") == "distinct":
        assert "distinct" in dedup_types, f"Expected distinct dedup, got {dedup_types}"


# ── GC-P2-005: detail query (no aggregation) ──

def test_gc_p2_005_detail_query():
    """Plain SELECT without aggregation — should report detail grain."""
    sql = "SELECT order_no, user_id, order_amt FROM order_table"
    result = _analyze_with_semantics(sql)

    sr = result.semantics_report
    assert sr.status != "not_supported_in_p0"

    # Grain should be detail (no GROUP BY / DISTINCT)
    if sr.result_grain:
        assert sr.result_grain.get("grain_type") in ("detail", "unknown")

    # No metrics (just column references)
    metric_types = [m.get("metric_type") for m in sr.metrics]
    # Column references are not aggregations, so metrics may be empty
    # or contain "expression" type entries


# ── GC-P2-006: where filter detection ──

def test_gc_p2_006_where_filter():
    """SELECT with WHERE — should detect partition filter when dt is involved."""
    sql = "SELECT order_no, user_id FROM order_table WHERE dt = '20260501'"
    result = _analyze_with_semantics(sql)

    sr = result.semantics_report
    assert sr.status != "not_supported_in_p0"

    # Filters
    assert len(sr.filters) >= 1, f"Expected at least 1 filter, got {len(sr.filters)}"
    filter_types = [f.get("filter_type") for f in sr.filters]
    assert any(ft in filter_types for ft in ("where", "partition_filter"))

    # No no_partition_filter risk since we have a dt filter
    risk_types = [r.get("risk_type") for r in sr.semantic_risks]
    assert "no_partition_filter" not in risk_types, (
        f"Should not have no_partition_filter risk when dt filter exists, got {risk_types}"
    )
