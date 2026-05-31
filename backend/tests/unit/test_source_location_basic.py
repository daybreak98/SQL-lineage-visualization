"""M18 (R09b1) SourceLocationExtractor 单元测试。

覆盖：
1. select 单字段定位
2. select 多字段 + 别名定位
3. from 表定位（单表 + 别名）
4. where 条件字段定位
5. group by 字段定位
6. order by 字段定位
7. 跨行 SQL 定位
8. 无法定位时的降级（unavailable）
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
    """运行完整解析管线，返回 (locations, diagnostics, scope_model, name_resolution)。"""
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
    return locations, diagnostics, scope_model, name_resolution


def _locations_by_entity(
    locations: list,
    entity_id: str,
) -> list:
    return [loc for loc in locations if loc.entity_id == entity_id]


def _locations_by_type(
    locations: list,
    entity_type: EntityType,
) -> list:
    return [loc for loc in locations if loc.entity_type == entity_type]


# ── Test 1: select 单字段定位 ──
class TestSelectSingleField:
    def test_single_column_location(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 应包含输出字段 order_no 的位置
        output_locs = _locations_by_type(locations, EntityType.output_column)
        assert len(output_locs) >= 1
        order_no_loc = output_locs[0]
        assert order_no_loc.range_type == "exact"
        assert order_no_loc.start_line == 1
        # "SELECT order_no..." → order_no starts at col 8
        assert order_no_loc.start_col == 8
        assert order_no_loc.end_col >= 15  # "order_no" is 8 chars, col 8+7=15
        assert order_no_loc.raw_text is not None
        assert "order_no" in order_no_loc.raw_text.lower()

    def test_single_field_entity_id(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 应绑定正确的 output_column entity_id
        output_locs = _locations_by_type(locations, EntityType.output_column)
        assert len(output_locs) >= 1
        assert output_locs[0].entity_id.startswith("output_column:")


# ── Test 2: select 多字段 + 别名定位 ──
class TestSelectMultiFieldAndAlias:
    def test_multi_field_locations(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT o.order_no AS no, o.user_id FROM order_table o"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        output_locs = _locations_by_type(locations, EntityType.output_column)
        assert len(output_locs) >= 2  # at least 2 output expressions

        # 第一个输出字段应包含 "no" 别名
        alias_texts = [
            loc.raw_text for loc in output_locs
            if loc.raw_text and "no" in loc.raw_text.lower()
        ]
        assert len(alias_texts) >= 1

    def test_alias_position(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        # 使用与 output_name 不同的别名，确保别名单独定位
        sql = "SELECT order_no AS order_num FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 找到别名 "order_num" 的定位
        alias_locs = [
            loc for loc in locations
            if loc.raw_text and "order_num" in loc.raw_text
        ]
        assert len(alias_locs) >= 1
        alias_loc = alias_locs[0]
        assert alias_loc.range_type == "exact"
        assert alias_loc.start_line == 1

    def test_table_alias_location(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table o"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 找到 table_alias 类型的定位
        alias_locs = _locations_by_type(locations, EntityType.table_alias)
        assert len(alias_locs) >= 1
        # 别名 "o" 应定位在 FROM order_table o 中的 o
        alias_loc = alias_locs[0]
        assert alias_loc.raw_text == "o"
        assert alias_loc.range_type == "exact"


# ── Test 3: from 表定位 ──
class TestFromTable:
    def test_single_table_location(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        table_locs = _locations_by_type(locations, EntityType.table)
        assert len(table_locs) >= 1
        table_loc = table_locs[0]
        assert table_loc.range_type == "exact"
        assert table_loc.start_line == 1
        assert "order_table" in table_loc.raw_text.lower()

    def test_table_entity_id(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        table_locs = _locations_by_type(locations, EntityType.table)
        assert len(table_locs) >= 1
        assert table_locs[0].entity_id.startswith("table:")


# ── Test 4: where 条件字段定位 ──
class TestWhereClause:
    def test_where_column_location(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        # WHERE 中的字段与 SELECT 不同，确保 text search 能正确定位
        sql = "SELECT order_no FROM order_table WHERE status = 1"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 应该有 WHERE 子句中的字段位置
        column_locs = _locations_by_type(locations, EntityType.column)
        assert len(column_locs) >= 1

        # WHERE 中的 status 在 SQL 后半部分
        status_locs = [
            loc for loc in column_locs
            if loc.raw_text and "status" in loc.raw_text.lower()
        ]
        assert len(status_locs) >= 1
        # status 应位于 "WHERE status" 之后，offset 较大
        assert status_locs[0].start_offset and status_locs[0].start_offset > 30

    def test_where_with_table_qualifier(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT * FROM order_table o WHERE o.order_no = 'ORD001'"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        column_locs = _locations_by_type(locations, EntityType.column)
        assert len(column_locs) >= 1

        # 应包含带表限定符 "o.order_no" 的引用
        qualified = [
            loc for loc in column_locs
            if loc.raw_text and "." in loc.raw_text
        ]
        assert len(qualified) >= 1
        assert "order_no" in qualified[0].raw_text.lower()


# ── Test 5: group by 字段定位 ──
class TestGroupBy:
    def test_group_by_column_location(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT status, COUNT(*) AS cnt "
            "FROM order_table "
            "GROUP BY status"
        )
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        column_locs = _locations_by_type(locations, EntityType.column)
        # 应有 GROUP BY 中的 status 和 SELECT 中的 status
        status_locs = [
            loc for loc in column_locs
            if loc.raw_text and "status" in loc.raw_text.lower()
        ]
        assert len(status_locs) >= 1


# ── Test 6: order by 字段定位 ──
class TestOrderBy:
    def test_order_by_column_location(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT order_no, order_amt "
            "FROM order_table "
            "ORDER BY order_amt DESC"
        )
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        column_locs = _locations_by_type(locations, EntityType.column)
        order_amt_locs = [
            loc for loc in column_locs
            if loc.raw_text and "order_amt" in loc.raw_text.lower()
        ]
        assert len(order_amt_locs) >= 1


# ── Test 7: 跨行 SQL 定位 ──
class TestMultiLineSql:
    def test_multiline_column_locations(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT\n"
            "    order_no,\n"
            "    user_id\n"
            "FROM order_table\n"
            "WHERE status = 1"
        )
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 验证所有位置都有有效的行号
        for loc in locations:
            assert loc.start_line >= 1
            if loc.range_type == "exact":
                assert loc.start_line <= 5  # 总共 5 行

        # 至少有一个在第 2 行
        line2_locs = [loc for loc in locations if loc.start_line == 2]
        assert len(line2_locs) >= 1

    def test_crlf_line_endings(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no\r\nFROM order_table\r\nWHERE status = 1"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 验证 CRLF 跨行正确处理
        table_locs = _locations_by_type(locations, EntityType.table)
        assert len(table_locs) >= 1
        # FROM 子句在其所在行
        from_line = table_locs[0].start_line
        assert from_line >= 1
        # 验证所有位置都有效
        for loc in locations:
            assert loc.start_line >= 1


# ── Test 8: 降级 unavailable ──
class TestUnavailable:
    def test_unavailable_with_empty_name_resolution(self):
        """无元数据时（name_resolution 为空），column 引用无法匹配到已知 entity_id，但位置仍尝试提取。"""
        sql = "SELECT missing_col FROM unknown_table"
        parse_service = SqlParseService()
        parse_result, _ = parse_service.parse(sql)

        scope_resolver = ScopeResolver()
        scope_model, _ = scope_resolver.resolve(parse_result)

        # 空的 name_resolution
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

        # 应有 source_locations 输出（即便 entity_id 降级为 scope_column）
        assert len(locations) > 0
        # 检查 entity_id 格式合法性（不抛异常即可）
        for loc in locations:
            assert loc.entity_id

    def test_missing_table_still_yields_location(self, repo_with_fixture):
        """即使元数据中没有该表，from 表定位仍应返回位置（物理表始终进入 lineage）。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT a FROM missing_table_xyz"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        table_locs = _locations_by_type(locations, EntityType.table)
        assert len(table_locs) >= 1
        # 即使表不在元数据中，也应定位到其位置
        table_loc = table_locs[0]
        assert "missing_table_xyz" in table_loc.raw_text.lower()
        assert table_loc.range_type == "exact"

    def test_unknown_column_still_has_location(self, repo_with_fixture):
        """元数据中不存在的列引用仍应产生 source_location（unavailable 或 synthetic）。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT no_such_column FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 至少有一个 location 指向该列文本
        found = [
            loc for loc in locations
            if loc.raw_text and "no_such_column" in loc.raw_text.lower()
        ]
        assert len(found) >= 1


# ── 附加测试：诊断输出 ──
class TestDiagnostics:
    def test_extractor_returns_diagnostics_list(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        _, diagnostics, _, _ = _run_pipeline(sql, meta_service)
        # diagnostics 应为 list
        assert isinstance(diagnostics, list)

    def test_no_crash_on_complex_sql(self, repo_with_fixture):
        """验证复杂 SQL 不会导致崩溃。"""
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = (
            "SELECT o.order_no, o.user_id, u.user_name\n"
            "FROM order_table o\n"
            "JOIN user_table u ON o.user_id = u.user_id\n"
            "WHERE o.status = 1\n"
            "GROUP BY o.user_id, u.user_name\n"
            "ORDER BY o.order_no DESC"
        )
        locations, diagnostics, _, _ = _run_pipeline(sql, meta_service)
        assert len(locations) > 0
        # 不应该有 error 级别的诊断（source_location 阶段不应产生 error）
        errors = [d for d in diagnostics if d.level.value == "error"]
        assert len(errors) == 0


# ── 契约测试 ──
class TestContract:
    def test_source_location_schema(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        for loc in locations:
            # 验证 SourceLocation 结构完整性
            assert loc.location_id.startswith("loc:")
            assert loc.entity_id
            assert loc.entity_type in EntityType.__members__.values()
            assert loc.range_type in ("exact", "synthetic", "unavailable")
            assert 0.0 <= loc.confidence <= 1.0
            if loc.range_type == "exact":
                assert loc.start_line is not None and loc.start_line >= 1
                assert loc.start_col is not None and loc.start_col >= 1
                assert loc.start_offset is not None and loc.start_offset >= 0

    def test_source_sql_id_consistent(self, repo_with_fixture):
        repo, _ = repo_with_fixture
        meta_service = MetadataService(repo)
        sql = "SELECT order_no FROM order_table"
        locations, _, _, _ = _run_pipeline(sql, meta_service)

        # 所有 location 应有相同的 source_sql_id
        sql_ids = {loc.source_sql_id for loc in locations}
        assert len(sql_ids) == 1
        assert sql_ids.pop() is not None
