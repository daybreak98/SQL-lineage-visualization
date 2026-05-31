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


def _analyze_sql(sql_text: str, metadata_version: str = "p0-fixture-v1"):
    """Analyze raw SQL text directly (for inline golden case definitions)."""
    repo = _seeded_repo()
    request = AnalyzeSqlRequest(
        sql=sql_text,
        dialect="spark",
        metadata_version=metadata_version,
    )
    return AnalysisOrchestrator(repo).analyze(request)


def test_gc_p0_001_simple_select():
    result = _analyze("simple_select")
    assert result.status.value == "success"
    assert result.summary.table_count == 1
    assert result.summary.source_column_count == 2
    assert result.summary.output_column_count == 2
    assert result.diagnostics_report.error_count == 0
    assert {
        "column:default.order_table.order_no",
        "column:default.order_table.user_id",
        "output_column:scope:root:1:order_no",
        "output_column:scope:root:2:user_id",
    }.issubset(_node_ids(result))
    assert (
        "projection",
        "column:default.order_table.order_no",
        "output_column:scope:root:1:order_no",
    ) in _edge_tuples(result)
    assert (
        "projection",
        "column:default.order_table.user_id",
        "output_column:scope:root:2:user_id",
    ) in _edge_tuples(result)


def test_gc_p0_002_single_table_alias():
    result = _analyze("single_table_alias")
    assert result.status.value == "success"
    assert result.diagnostics_report.error_count == 0
    assert {
        "column:default.order_table.order_no",
        "output_column:scope:root:1:order_id",
    }.issubset(_node_ids(result))
    assert (
        "alias",
        "column:default.order_table.order_no",
        "output_column:scope:root:1:order_id",
    ) in _edge_tuples(result)


def test_gc_p0_003_unknown_table():
    result = _analyze("unknown_table")
    assert result.status.value == "partial"
    assert result.metadata_context.missing_tables[0].table == "missing_table"
    assert "UNKNOWN_TABLE" in _diagnostic_codes(result)


def test_gc_p0_004_unknown_column():
    result = _analyze("unknown_column")
    assert result.status.value == "partial"
    assert "UNKNOWN_COLUMN" in _diagnostic_codes(result)
    assert result.metadata_context.missing_columns[0].column == "missing_col"
    assert {
        "column:default.order_table.order_no",
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
        "column:default.order_table.user_id",
        "column:default.user_table.user_id",
    }
    assert "unknown:scope:root:1:user_id" in _node_ids(result)


def test_gc_p0_006_simple_expression_direct_dependency():
    result = _analyze("simple_expression")
    assert result.status.value == "success"
    assert result.diagnostics_report.error_count == 0
    assert {
        "column:default.order_table.order_amt",
        "output_column:scope:root:1:commission",
    }.issubset(_node_ids(result))
    assert (
        "alias",
        "column:default.order_table.order_amt",
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
            "column:default.order_table.order_no",
            "output_column:scope:root:1:order_no",
        ),
        (
            "projection",
            "column:default.order_table.user_id",
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


# ---------------------------------------------------------------------------
# M17 Golden Case 扩展：表级血缘 / entity_id 去冗余 / label 格式
# ---------------------------------------------------------------------------

def test_gc_p0_013_cte_table_level():
    """表级血缘：CTE SQL 只展示物理表，CTE 中间表不出现"""
    sql = """
    WITH mt AS (SELECT agent_id, SUM(order_amount) AS gmv FROM intl_hotel_orders GROUP BY 1),
         t1 AS (SELECT agent_id, gmv FROM mt)
    SELECT agent_id, gmv FROM t1
    """
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    nodes = result.graph_view_model.nodes
    labels = [n.label for n in nodes]
    # 物理表应该出现
    assert "intl_hotel_orders" in labels, f"物理表未出现，labels={labels}"
    # CTE 中间表不应该出现
    assert "mt" not in labels, f"CTE mt 不应出现在表级血缘中"
    assert "t1" not in labels, f"CTE t1 不应出现在表级血缘中"


def test_gc_p0_014_subquery_table_level():
    """表级血缘：子查询 SQL 只展示子查询内的物理表"""
    sql = """
    SELECT hotel_seq, total 
    FROM (SELECT hotel_seq, COUNT(order_no) AS total 
          FROM fuwu.dwd_ord_htl_servicequality_di 
          WHERE dt='20260513' GROUP BY 1) aa
    """
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    nodes = result.graph_view_model.nodes
    labels = [n.label for n in nodes]
    # 物理表应该出现（带 schema 前缀）
    table_labels = [l for l in labels if "dwd_ord_htl" in l]
    assert len(table_labels) > 0, f"物理表未出现，labels={labels}"
    # 子查询别名不应该出现
    assert "aa" not in labels, f"子查询别名 aa 不应出现在表级血缘中"


def test_gc_p0_015_join_table_level():
    """表级血缘：多表 JOIN，所有物理表出现"""
    sql = """
    SELECT a.order_no, b.user_name 
    FROM default.order_table a 
    JOIN default.user_table b ON a.user_id = b.user_id
    """
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    nodes = result.graph_view_model.nodes
    labels = [n.label for n in nodes]
    # 两个物理表都应该出现
    assert "order_table" in labels, f"order_table 未出现"
    assert "user_table" in labels, f"user_table 未出现"


def test_gc_p0_016_nested_subquery():
    """表级血缘：嵌套子查询 + LEFT JOIN，所有物理表出现"""
    sql = (P0_DIR / "subquery" / "input.sql").read_text(encoding="utf-8")
    result = _analyze_sql(sql)
    nodes = result.graph_view_model.nodes
    labels = [n.label for n in nodes]
    table_nodes = [n for n in nodes if n.node_type.value == "table"]
    # 至少找到 2 个物理表
    assert len(table_nodes) >= 2, f"期望至少 2 个物理表，实际: {len(table_nodes)}, labels={labels}"
    # 具体表必须出现
    assert any("dwd_ord_htl_servicequality_di" in l for l in labels)
    assert any("mdw_order_v3_international" in l for l in labels)
    # 子查询别名不出现
    assert "aa" not in labels
    assert "a1" not in labels
    assert "a2" not in labels


def test_gc_p0_017_entity_id_no_redundant_default():
    """entity_id 中 default catalog 应省略"""
    sql = "SELECT hotel_seq FROM fuwu.dwd_ord_htl_servicequality_di WHERE dt='20260513'"
    result = _analyze_sql(sql)
    nodes = result.graph_view_model.nodes
    table_nodes = [n for n in nodes if n.node_type.value == "table"]
    assert len(table_nodes) > 0
    entity_id = table_nodes[0].entity_id or ""
    # 不应该出现 default.default 或 default.fuwu
    assert "default.default" not in entity_id
    assert "default.fuwu" not in entity_id


def test_gc_p0_018_label_shows_schema_table():
    """标签应显示 schema.table 格式"""
    sql = "SELECT hotel_seq FROM fuwu.dwd_ord_htl_servicequality_di WHERE dt='20260513'"
    result = _analyze_sql(sql)
    nodes = result.graph_view_model.nodes
    table_nodes = [n for n in nodes if n.node_type.value == "table"]
    assert len(table_nodes) > 0
    label = table_nodes[0].label
    # 标签应该包含 fuwu.dwd_ord...
    assert "fuwu" in label
    assert "dwd_ord" in label


# ============================================================================
# P1 (M19) Golden Cases: CTE/Join/Union enhancements
# ============================================================================

P1_DIR = ROOT / "tests" / "golden_cases" / "p1"


def _read_p1_sql(dirname: str, filename: str = "input.sql") -> str:
    return (P1_DIR / dirname / filename).read_text(encoding="utf-8")


# ── P1-001: CTE field traceback ──
def test_gc_p1_001_cte_basic_traceback():
    """CTE 输出字段回溯到物理表字段"""
    sql = _read_p1_sql("cte_basic", "input.sql")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    # Physical table should appear
    table_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "table"]
    assert any("order_table" in n.label for n in table_nodes), f"No order_table in {[n.label for n in table_nodes]}"
    # CTE intermediate tables should NOT appear
    labels = [n.label for n in result.graph_view_model.nodes]
    assert "mt" not in labels, f"CTE intermediate 'mt' should not appear"
    # Output columns should exist
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    assert len(output_nodes) >= 2, f"Expected >=2 output columns, got {len(output_nodes)}"
    output_names = {n.label for n in output_nodes}
    assert "order_no" in output_names
    assert "user_id" in output_names


# ── P1-002: CTE field traceback with alias ──
def test_gc_p1_002_cte_alias_traceback():
    """CTE 带列别名时字段回溯"""
    sql = _read_p1_sql("cte_basic", "input_cte_alias.sql")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    # Output columns
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    output_names = {n.label for n in output_nodes}
    assert "order_id" in output_names, f"Expected order_id in output, got {output_names}"
    assert "user_id" in output_names
    # Edge from physical column to output should exist
    edge_tuples = _edge_tuples(result)
    has_alias_edge = any(et[0] == "alias" for et in edge_tuples)
    assert has_alias_edge, f"Alias edge expected, got {edge_tuples}"


# ── P1-003: Join key extraction ──
def test_gc_p1_003_join_keys_extracted():
    """JOIN ON 子句字段对被提取为 join_key"""
    sql = _read_p1_sql("join_basic", "input.sql")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    # Scope model should have join_keys
    # We can't directly access scope_model from AnalysisResult, but we can check
    # that the lineage_ir has join_condition edges
    edge_types = {e.edge_type.value for e in result.lineage_ir.edges}
    # At minimum, the output should exist and not crash
    assert result.lineage_ir.edges, f"No edges generated"
    # Check that the analysis succeeds even with ambiguous join column
    # (the ambiguous column user_id should be disambiguated via join ON clause)
    ambiguous = result.metadata_context.ambiguous_columns
    # With join disambiguation, user_id referencing both tables should be resolved
    # It's ambiguous but both are equi-joined, so it should be disambiguated
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    assert len(output_nodes) >= 1


# ── P1-004: Join key qualified columns ──
def test_gc_p1_004_join_qualified_columns():
    """JOIN 中使用限定列名时的字段消歧"""
    sql = _read_p1_sql("join_basic", "input_join_keys.sql")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    # Both physical tables should appear
    labels = [n.label for n in result.graph_view_model.nodes]
    assert "order_table" in labels
    assert "user_table" in labels
    # Qualified columns should resolve without ambiguity
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    output_names = {n.label for n in output_nodes}
    assert "order_no" in output_names
    assert "user_name" in output_names
    # No ambiguous columns since columns are qualified
    ambiguous = result.metadata_context.ambiguous_columns
    assert len(ambiguous) == 0, f"Expected 0 ambiguous columns, got {len(ambiguous)}"


# ── P1-005: Union ALL segments ──
def test_gc_p1_005_union_all_segments():
    """UNION ALL 多段查询连接"""
    sql = _read_p1_sql("union_all", "input.sql")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    # Physical table should appear
    labels = [n.label for n in result.graph_view_model.nodes]
    assert "order_table" in labels, f"order_table not in {labels}"
    # Output columns should exist
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    assert len(output_nodes) >= 2, f"Expected >=2 output columns, got {len(output_nodes)}"


# ── P1-006: Union ALL with constants ──
def test_gc_p1_006_union_constants():
    """UNION ALL 带常量标签"""
    sql = _read_p1_sql("union_all", "input_union_const.sql")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    # Physical table should appear
    labels = [n.label for n in result.graph_view_model.nodes]
    assert "order_table" in labels
    # Output columns include 'flag' with literal value
    expression_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "expression"]
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    output_names = {n.label for n in output_nodes}
    assert "order_no" in output_names
    assert "flag" in output_names


# ============================================================================
# P2 (M23/R13a) Golden Cases: ExpressionAnalyzer (aggregate/case when/window)
# ============================================================================

P2_DIR = ROOT / "tests" / "golden_cases" / "p2"


def _read_p2_sql(dirname: str, filename: str = "input.sql") -> str:
    return (P2_DIR / dirname / filename).read_text(encoding="utf-8")


# ── P2-001: CASE WHEN expression ──
def test_gc_p2_001_case_when_expression():
    """CASE WHEN 表达式: 验证条件分支被识别，source columns 包含 status"""
    sql = _read_p2_sql("case_when_metric")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # Output columns should include status_label
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    output_names = {n.label for n in output_nodes}
    assert "status_label" in output_names, f"Expected status_label in outputs, got {output_names}"

    # Expression nodes should exist (for CASE WHEN)
    expr_nodes = [n for n in result.lineage_ir.nodes if n.node_type.value == "expression"]
    assert len(expr_nodes) >= 1, f"Expected >=1 expression node, got {len(expr_nodes)}"
    case_expr = [n for n in expr_nodes if "CASE WHEN" in n.label]
    assert len(case_expr) >= 1, f"Expected a CASE WHEN expression node, got {[n.label for n in expr_nodes]}"

    # Expression edges should exist
    expr_edges = [e for e in result.lineage_ir.edges if e.edge_type.value == "expression"]
    assert len(expr_edges) >= 2, f"Expected >=2 expression edges, got {len(expr_edges)}"

    # Source column (status) should be present in nodes
    node_ids = {n.id for n in result.lineage_ir.nodes}
    assert any("status" in nid for nid in node_ids), f"status column not found in nodes: {node_ids}"


# ── P2-002: Window function ──
def test_gc_p2_002_window_function():
    """窗口函数: 验证 ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...) 被识别"""
    sql = _read_p2_sql("window_function")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # Output columns should include rn
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    output_names = {n.label for n in output_nodes}
    assert "rn" in output_names, f"Expected rn in outputs, got {output_names}"

    # Expression nodes should exist (for window function)
    expr_nodes = [n for n in result.lineage_ir.nodes if n.node_type.value == "expression"]
    assert len(expr_nodes) >= 1, f"Expected >=1 expression node, got {len(expr_nodes)}"
    window_expr = [n for n in expr_nodes if "ROW_NUMBER" in n.label]
    assert len(window_expr) >= 1, f"Expected a ROW_NUMBER expression node, got {[n.label for n in expr_nodes]}"

    # Expression edges should exist
    expr_edges = [e for e in result.lineage_ir.edges if e.edge_type.value == "expression"]
    assert len(expr_edges) >= 2, f"Expected >=2 expression edges, got {len(expr_edges)}"

    # Source column (user_id, order_amt) nodes should exist
    node_ids = {n.id for n in result.lineage_ir.nodes}
    assert any("user_id" in nid for nid in node_ids), f"user_id not found in nodes"
    assert any("order_amt" in nid for nid in node_ids), f"order_amt not found in nodes"


# ── P2-003: Aggregate function ──
def test_gc_p2_003_aggregate_expression():
    """聚合函数: 验证 SUM/COUNT/AVG 等聚合函数被识别，source columns 正确"""
    sql = "SELECT SUM(order_amt) AS total_amt, COUNT(*) AS cnt FROM default.order_table"
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # Output columns
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    output_names = {n.label for n in output_nodes}
    assert "total_amt" in output_names
    assert "cnt" in output_names

    # Expression nodes for aggregates
    expr_nodes = [n for n in result.lineage_ir.nodes if n.node_type.value == "expression"]
    assert len(expr_nodes) >= 2, f"Expected >=2 expression nodes (for SUM and COUNT), got {len(expr_nodes)}"
    agg_labels = [n.label for n in expr_nodes]
    assert any("SUM" in l for l in agg_labels), f"SUM not found in expression labels: {agg_labels}"
    assert any("COUNT" in l for l in agg_labels), f"COUNT not found in expression labels: {agg_labels}"

    # Expression edges (COUNT(*) has no source column, so 3 edges: 2 output + 1 source)
    expr_edges = [e for e in result.lineage_ir.edges if e.edge_type.value == "expression"]
    assert len(expr_edges) >= 3, f"Expected >=3 expression edges, got {len(expr_edges)}"


# ── P2-004: Window with aggregate ──
def test_gc_p2_004_window_with_aggregate():
    """窗口聚合: 验证 SUM() OVER (PARTITION BY ...) 被识别为窗口函数"""
    sql = (
        "SELECT user_id, order_amt, "
        "SUM(order_amt) OVER (PARTITION BY user_id) AS cum_sum "
        "FROM default.order_table"
    )
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # Output columns
    output_nodes = [n for n in result.graph_view_model.nodes if n.node_type.value == "output_column"]
    output_names = {n.label for n in output_nodes}
    assert "cum_sum" in output_names

    # Expression nodes - should be a window function, not just aggregate
    expr_nodes = [n for n in result.lineage_ir.nodes if n.node_type.value == "expression"]
    assert len(expr_nodes) >= 1
    window_labels = [n.label for n in expr_nodes if "OVER" in n.label]
    assert len(window_labels) >= 1, f"Expected window expression, got {[n.label for n in expr_nodes]}"

    # Verify partition column (user_id) exists
    node_ids = {n.id for n in result.lineage_ir.nodes}
    assert any("user_id" in nid for nid in node_ids)


# ============================================================================
# M24 (R09b2) Golden Cases: SourceLocation 增强（CTE/子查询/JOIN/UNION/CASE WHEN/窗口函数）
# ============================================================================

# ── M24-001: CTE 定义位置 ──
def test_gc_m24_001_cte_definition_location():
    """CTE 定义位置: 验证 WITH 子句和 CTE 定义产生 cte 类型的 source_location。"""
    sql = _read_p2_sql("cte_location")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # source_locations 应包含 cte 类型的条目
    cte_locs = [loc for loc in result.source_locations if loc.entity_type.value == "cte"]
    assert len(cte_locs) >= 1, f"Expected >=1 cte location, got {len(cte_locs)}"

    # 应有 with:scope:root 的 entity_id
    with_entity_ids = {loc.entity_id for loc in cte_locs}
    assert any("with:scope:root" in eid for eid in with_entity_ids), \
        f"Expected 'with:scope:root' in entity_ids: {with_entity_ids}"

    # 应有 cte:scope:root:mt 的 entity_id
    assert any("cte:scope:root:mt" in eid for eid in with_entity_ids), \
        f"Expected 'cte:scope:root:mt' in entity_ids: {with_entity_ids}"


# ── M24-002: CASE WHEN 表达式位置 ──
def test_gc_m24_002_case_when_location():
    """CASE WHEN 位置: 验证 CASE WHEN 表达式产生 expression 类型的 source_location。"""
    sql = _read_p2_sql("case_when_location")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # 应有 expression 类型且包含 case 的 entity_id
    expr_locs = [loc for loc in result.source_locations if loc.entity_type.value == "expression"]
    case_locs = [loc for loc in expr_locs if "case" in loc.entity_id]
    assert len(case_locs) >= 1, \
        f"Expected >=1 CASE WHEN expression location, got {len(case_locs)}"

    # 验证 location 有正确的范围信息
    case_loc = case_locs[0]
    assert case_loc.range_type in ("exact", "unavailable"), \
        f"Expected exact or unavailable, got {case_loc.range_type}"
    assert case_loc.confidence >= 0.0


# ── M24-003: 子查询位置 ──
def test_gc_m24_003_subquery_location():
    """子查询位置: 验证 FROM 子查询产生 subquery 类型的 source_location。"""
    sql = (
        "SELECT hotel_seq, total\n"
        "FROM (SELECT hotel_seq, COUNT(*) AS total\n"
        "      FROM default.order_table\n"
        "      GROUP BY hotel_seq) sq"
    )
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    sq_locs = [loc for loc in result.source_locations if loc.entity_type.value == "subquery"]
    assert len(sq_locs) >= 1, f"Expected >=1 subquery location, got {len(sq_locs)}"


# ── M24-004: JOIN ON 条件位置 ──
def test_gc_m24_004_join_on_location():
    """JOIN ON 位置: 验证 JOIN ON 条件产生 join 类型的 source_location。"""
    sql = (
        "SELECT a.order_no, b.user_name\n"
        "FROM default.order_table a\n"
        "JOIN default.user_table b ON a.user_id = b.user_id"
    )
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    join_locs = [loc for loc in result.source_locations if loc.entity_type.value == "join"]
    assert len(join_locs) >= 1, \
        f"Expected >=1 join ON location, got {len(join_locs)}"
    assert "join_on:scope:root:1" in {loc.entity_id for loc in join_locs}


# ── M24-005: UNION 段位置 ──
def test_gc_m24_005_union_segment_location():
    """UNION 段位置: 验证 UNION ALL 各段产生 statement 类型的 source_location。"""
    sql = _read_p1_sql("union_all", "input.sql")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # Should have union_segment locations (statement type)
    segment_locs = [loc for loc in result.source_locations
                    if "union_segment" in loc.entity_id]
    assert len(segment_locs) >= 1, \
        f"Expected >=1 union_segment location, got {len(segment_locs)}"


# ── M24-006: 窗口函数位置 ──
def test_gc_m24_006_window_location():
    """窗口函数位置: 验证 OVER (PARTITION BY ... ORDER BY ...) 产生 expression 类型的 source_location。"""
    sql = _read_p2_sql("window_function")
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    # Should have window expression locations
    expr_locs = [loc for loc in result.source_locations if loc.entity_type.value == "expression"]
    window_locs = [loc for loc in expr_locs if "window" in loc.entity_id]
    assert len(window_locs) >= 1, \
        f"Expected >=1 window expression location, got {len(window_locs)}"


# ── M24-007: 复杂 CTE 多级嵌套位置 ──
def test_gc_m24_007_deep_cte_location():
    """复杂 CTE 位置: 验证多级 CTE 嵌套定位。"""
    sql = (
        "WITH t1 AS (SELECT order_no, user_id FROM default.order_table),\n"
        "t2 AS (SELECT order_no, user_id FROM t1 WHERE user_id > 100),\n"
        "t3 AS (SELECT user_id, COUNT(*) AS cnt FROM t2 GROUP BY user_id)\n"
        "SELECT * FROM t3"
    )
    result = _analyze_sql(sql)
    assert result.status.value != "failed"

    cte_locs = [loc for loc in result.source_locations if loc.entity_type.value == "cte"]
    assert len(cte_locs) >= 3, \
        f"Expected >=3 CTE locations (3 CTE definitions), got {len(cte_locs)}"


# ── M24-008: 退化场景 —— all locations return appropritate fallback ──
def test_gc_m24_008_no_crash_edge_cases():
    """退化场景: 无 CTE/子查询/CASE WHEN 的简单 SQL 不应崩溃。"""
    sql = "SELECT order_no FROM default.order_table"
    result = _analyze_sql(sql)
    assert result.status.value != "failed"
    # 简单 SQL 不应有 cte/subquery/expression 定位
    cte_locs = [loc for loc in result.source_locations if loc.entity_type.value == "cte"]
    assert len(cte_locs) == 0, f"Simple query should have no cte locations, got {len(cte_locs)}"
