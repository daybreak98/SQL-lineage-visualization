"""M20 (R11a): StarExpander unit tests.

精简单元测试（仅 2 个）:
1. test_star_expand_basic — 单表 * 展开成功，字段数量正确
2. test_star_expand_alias — alias.* 展开正确
"""

from app.domain.contracts import DiagnosticCode
from app.repositories.metadata_repository import MetadataRepository
from app.services.metadata_service import MetadataService
from app.services.name_resolver import NameResolver
from app.services.scope_resolver import ScopeResolver
from app.services.sql_parse_service import SqlParseService
from app.services.star_expander import StarExpander


def _seed(repo: MetadataRepository) -> None:
    """Seed metadata with 5 columns for order_table."""
    repo.create_metadata_version("v1")
    order_id = repo.upsert_table("v1", "default", "default", "order_table", "order_table")
    repo.upsert_columns(
        order_id,
        "v1",
        [
            {"column_name": "order_no", "normalized_column_name": "order_no", "data_type": "string", "ordinal": 1},
            {"column_name": "user_id", "normalized_column_name": "user_id", "data_type": "bigint", "ordinal": 2},
            {"column_name": "order_amt", "normalized_column_name": "order_amt", "data_type": "decimal", "ordinal": 3},
            {"column_name": "status", "normalized_column_name": "status", "data_type": "int", "ordinal": 4},
            {"column_name": "dt", "normalized_column_name": "dt", "data_type": "string", "ordinal": 5},
        ],
    )
    user_id = repo.upsert_table("v1", "default", "default", "user_table", "user_table")
    repo.upsert_columns(
        user_id,
        "v1",
        [
            {"column_name": "user_id", "normalized_column_name": "user_id", "data_type": "bigint", "ordinal": 1},
            {"column_name": "user_name", "normalized_column_name": "user_name", "data_type": "string", "ordinal": 2},
        ],
    )


def _resolve(sql: str, repo: MetadataRepository):
    """Run scope resolution + name resolution to get scope_model and name_resolution."""
    parsed, _ = SqlParseService().parse(sql)
    scope_model, _ = ScopeResolver().resolve(parsed)
    name_resolution, _ = NameResolver(MetadataService(repo)).resolve(
        scope_model, metadata_version="v1",
    )
    return scope_model, name_resolution


# ── Test 1: single table * expansion ──

def test_star_expand_basic(repo):
    """SELECT * FROM order_table 展开为 5 个字段"""
    _seed(repo)
    scope_model, name_resolution = _resolve("SELECT * FROM order_table", repo)

    expander = StarExpander(MetadataService(repo))
    expanded_items, extra_resolved, diagnostics = expander.expand(
        scope_model, name_resolution, metadata_version="v1",
    )

    # No diagnostics expected (metadata is available)
    assert diagnostics == []

    # 5 columns from order_table
    assert len(expanded_items) == 5, f"Expected 5 expanded items, got {len(expanded_items)}"
    assert len(extra_resolved) == 5

    # Check all expected column names are present
    output_names = {item.output_name for item in expanded_items}
    expected_names = {"order_no", "user_id", "order_amt", "status", "dt"}
    assert output_names == expected_names, f"Got {output_names}"

    # Check ordinals are sequential 1-5
    ordinals = [item.ordinal for item in expanded_items]
    assert ordinals == [1, 2, 3, 4, 5]

    # Each item should have expression_kind "column"
    for item in expanded_items:
        assert item.expression_kind == "column"
        assert item.source_columns, f"Item {item.output_name} has no source_columns"

    # Check resolved column entity IDs
    resolved_entity_ids = {rc.column_entity_id for rc in extra_resolved}
    expected_ids = {
        "column:default.order_table.order_no",
        "column:default.order_table.user_id",
        "column:default.order_table.order_amt",
        "column:default.order_table.status",
        "column:default.order_table.dt",
    }
    assert resolved_entity_ids == expected_ids


# ── Test 2: alias.* expansion ──

def test_star_expand_alias(repo):
    """SELECT o.* FROM order_table o 展开为 5 个字段（带别名限定）"""
    _seed(repo)
    scope_model, name_resolution = _resolve("SELECT o.* FROM order_table o", repo)

    expander = StarExpander(MetadataService(repo))
    expanded_items, extra_resolved, diagnostics = expander.expand(
        scope_model, name_resolution, metadata_version="v1",
    )

    assert diagnostics == []
    assert len(expanded_items) == 5
    assert len(extra_resolved) == 5

    output_names = {item.output_name for item in expanded_items}
    expected_names = {"order_no", "user_id", "order_amt", "status", "dt"}
    assert output_names == expected_names

    # Each source_column should reference the alias "o"
    for item in expanded_items:
        for sc in item.source_columns:
            assert sc.table == "o", f"Expected table='o' in source, got {sc.table}"
