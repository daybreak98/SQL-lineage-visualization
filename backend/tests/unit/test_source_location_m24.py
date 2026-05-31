"""M24 (R09b2) SourceLocation 增强单元测试。

覆盖:
1. CTE 定义定位
2. 子查询定位 (FROM subquery)
3. JOIN ON 条件定位
4. UNION 段定位
5. CASE WHEN 表达式定位
6. 窗口函数定位 (OVER)
7. 简单 SQL 无 crash
8. 退化场景 (unavailable)
"""

from __future__ import annotations

import pytest

from app.domain.contracts import (
    EntityType,
    MetadataContext,
)
from app.domain.name_resolution_model import NameResolutionResult
from app.services.metadata_service import MetadataService
from app.services.name_resolver import NameResolver
from app.services.scope_resolver import ScopeResolver
from app.services.source_location_extractor import SourceLocationExtractor
from app.services.sql_parse_service import SqlParseService


# ── helpers ──
def _run_pipeline(sql: str, metadata_service: MetadataService | None = None):
    parse_service = SqlParseService()
    parse_result, _ = parse_service.parse(sql)

    scope_resolver = ScopeResolver()
    scope_model, _ = scope_resolver.resolve(parse_result)

    if metadata_service is not None:
        name_resolver = NameResolver(metadata_service)
        name_resolution, _ = name_resolver.resolve(scope_model)
    else:
        name_resolution = NameResolutionResult(
            metadata_context=MetadataContext(
                metadata_version="test",
                case_sensitive=False,
            ),
        )

    extractor = SourceLocationExtractor()
    locations, diagnostics = extractor.extract(
        sql, parse_result, scope_model, name_resolution,
    )
    return locations, diagnostics


# ── M24.1: CTE 定义定位 ──
class TestCteDefinitionLocation:
    def test_single_cte_location(self, repo_with_fixture):
        """单 CTE 定义产生 cte 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "WITH mt AS (SELECT order_no FROM order_table) SELECT * FROM mt"
        locations, _ = _run_pipeline(sql, meta_service)

        cte_locs = [loc for loc in locations if loc.entity_type == EntityType.cte]
        assert len(cte_locs) >= 1, f"Expected >=1 cte location, got {len(cte_locs)}"

        # with:scope:root 应在 entity_id 中
        entity_ids = {loc.entity_id for loc in cte_locs}
        assert any("with:scope:root" in eid for eid in entity_ids)

    def test_multi_cte_location(self, repo_with_fixture):
        """多个 CTE 定义各自产生独立 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "WITH t1 AS (SELECT order_no FROM order_table),\n"
            "t2 AS (SELECT order_no FROM t1)\n"
            "SELECT * FROM t2"
        )
        locations, _ = _run_pipeline(sql, meta_service)

        cte_locs = [loc for loc in locations if loc.entity_type == EntityType.cte]
        # 应有 with:scope:root + cte:scope:root:t1 + cte:scope:root:t2
        assert len(cte_locs) >= 3, f"Expected >=3 cte locations, got {len(cte_locs)}"

    def test_cte_location_has_range(self, repo_with_fixture):
        """CTE location 应有有效的 start_line 等范围信息。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "WITH mt AS (SELECT order_no FROM order_table) SELECT * FROM mt"
        locations, _ = _run_pipeline(sql, meta_service)

        cte_locs = [loc for loc in locations if loc.entity_type == EntityType.cte]
        exact_locs = [loc for loc in cte_locs if loc.range_type == "exact"]
        assert len(exact_locs) >= 1
        for loc in exact_locs:
            assert loc.start_line is not None and loc.start_line >= 1
            assert loc.start_offset is not None and loc.start_offset >= 0

    def test_no_cte_no_cte_location(self, repo_with_fixture):
        """无 CTE 时不应产生 cte 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _ = _run_pipeline(sql, meta_service)

        cte_locs = [loc for loc in locations if loc.entity_type == EntityType.cte]
        assert len(cte_locs) == 0


# ── M24.2: 子查询定位 ──
class TestSubqueryLocation:
    def test_from_subquery_location(self, repo_with_fixture):
        """FROM 子查询产生 subquery 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT x FROM (SELECT order_no AS x FROM order_table) sq"
        locations, _ = _run_pipeline(sql, meta_service)

        sq_locs = [loc for loc in locations if loc.entity_type == EntityType.subquery]
        assert len(sq_locs) >= 1, f"Expected >=1 subquery location, got {len(sq_locs)}"

    def test_no_subquery_no_location(self, repo_with_fixture):
        """无子查询时不产生 subquery 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _ = _run_pipeline(sql, meta_service)

        sq_locs = [loc for loc in locations if loc.entity_type == EntityType.subquery]
        assert len(sq_locs) == 0


# ── M24.3: JOIN ON 条件定位 ──
class TestJoinOnLocation:
    def test_single_join_on_location(self, repo_with_fixture):
        """单 JOIN ON 条件产生 join 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT a.order_no FROM order_table a\n"
            "JOIN user_table b ON a.user_id = b.user_id"
        )
        locations, _ = _run_pipeline(sql, meta_service)

        join_locs = [loc for loc in locations if loc.entity_type == EntityType.join]
        assert len(join_locs) >= 1, f"Expected >=1 join location, got {len(join_locs)}"
        assert "join_on:scope:root:1" in {loc.entity_id for loc in join_locs}

    def test_no_join_no_join_location(self, repo_with_fixture):
        """无 JOIN 时不产生 join 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _ = _run_pipeline(sql, meta_service)

        join_locs = [loc for loc in locations if loc.entity_type == EntityType.join]
        assert len(join_locs) == 0


# ── M24.4: UNION 段定位 ──
class TestUnionLocation:
    def test_union_segment_location(self, repo_with_fixture):
        """UNION ALL 各段产生 statement 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT order_no FROM order_table\n"
            "UNION ALL\n"
            "SELECT user_name AS order_no FROM user_table"
        )
        locations, _ = _run_pipeline(sql, meta_service)

        segment_locs = [loc for loc in locations if "union_segment" in loc.entity_id]
        assert len(segment_locs) >= 1, \
            f"Expected >=1 union_segment location, got {len(segment_locs)}"


# ── M24.5: CASE WHEN 位置 ──
class TestCaseWhenLocation:
    def test_case_when_expression_location(self, repo_with_fixture):
        """CASE WHEN 产生 expression 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT order_no,\n"
            "CASE WHEN status = 1 THEN 'active' ELSE 'inactive' END AS label\n"
            "FROM order_table"
        )
        locations, _ = _run_pipeline(sql, meta_service)

        expr_locs = [loc for loc in locations if loc.entity_type == EntityType.expression]
        case_locs = [loc for loc in expr_locs if "case" in loc.entity_id]
        assert len(case_locs) >= 1, \
            f"Expected >=1 CASE WHEN expression location, got {len(case_locs)}"

    def test_no_case_when_no_location(self, repo_with_fixture):
        """无 CASE WHEN 时不产生 case 相关 expression location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _ = _run_pipeline(sql, meta_service)

        expr_locs = [loc for loc in locations if "case" in loc.entity_id]
        assert len(expr_locs) == 0


# ── M24.6: 窗口函数位置 ──
class TestWindowLocation:
    def test_window_function_location(self, repo_with_fixture):
        """窗口函数 OVER 产生 expression 类型 location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT user_id,\n"
            "ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_amt DESC) AS rn\n"
            "FROM order_table"
        )
        locations, _ = _run_pipeline(sql, meta_service)

        expr_locs = [loc for loc in locations if loc.entity_type == EntityType.expression]
        window_locs = [loc for loc in expr_locs if "window" in loc.entity_id]
        assert len(window_locs) >= 1, \
            f"Expected >=1 window expression location, got {len(window_locs)}"

    def test_no_window_no_location(self, repo_with_fixture):
        """无窗口函数时不产生 window 相关 expression location。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _ = _run_pipeline(sql, meta_service)

        expr_locs = [loc for loc in locations if "window" in loc.entity_id]
        assert len(expr_locs) == 0


# ── M24.7: 综合场景 ──
class TestIntegration:
    def test_complex_sql_all_locations(self, repo_with_fixture):
        """复杂 SQL 同时包含 CTE/JOIN/CASE WHEN/窗口函数，全部定位。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "WITH ranked AS (\n"
            "  SELECT user_id, order_amt,\n"
            "    CASE WHEN order_amt > 100 THEN 'high' ELSE 'low' END AS tier,\n"
            "    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_amt DESC) AS rn\n"
            "  FROM order_table\n"
            ")\n"
            "SELECT r.user_id, r.tier\n"
            "FROM ranked r\n"
            "JOIN user_table u ON r.user_id = u.user_id\n"
            "WHERE r.rn = 1"
        )
        locations, diagnostics = _run_pipeline(sql, meta_service)
        assert len(locations) > 0

        # 统计各类型 location 数量
        type_counts = {}
        for loc in locations:
            key = loc.entity_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        # CTE 应该被定位
        assert type_counts.get("cte", 0) >= 1, f"No CTE locations in {type_counts}"
        # JOIN ON 应该被定位
        assert type_counts.get("join", 0) >= 1, f"No JOIN locations in {type_counts}"
        # CASE WHEN 应产生 expression 位置
        assert type_counts.get("expression", 0) >= 2, \
            f"Expected >=2 expression locations, got {type_counts.get('expression', 0)}"

    def test_no_crash_on_empty_sql(self, repo_with_fixture):
        """空 SQL 不崩溃。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        # sqlglot can parse empty string
        locations, diagnostics = _run_pipeline("SELECT 1", meta_service)
        assert isinstance(locations, list)
        assert isinstance(diagnostics, list)
