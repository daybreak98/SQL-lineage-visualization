from app.domain.contracts import DiagnosticCode
from app.services.scope_resolver import ScopeResolver
from app.services.sql_parse_service import SqlParseService


def _parse(sql: str):
    result, diagnostics = SqlParseService().parse(sql)
    assert result.success, diagnostics
    return result


def test_scope_resolver_extracts_main_relations_and_aliases():
    parse_result = _parse(
        "SELECT o.order_no, u.user_name "
        "FROM order_table o JOIN user_table u ON o.user_id = u.user_id"
    )
    model, diagnostics = ScopeResolver().resolve(parse_result)
    assert diagnostics == []
    assert [r.alias for r in model.relations] == ["o", "u"]
    assert [r.table for r in model.relations] == ["order_table", "user_table"]
    assert model.relations[0].table_entity_id == "table:default.default.order_table"


def test_scope_resolver_extracts_schema_table():
    parse_result = _parse("SELECT order_no FROM ods.order_table")
    model, _ = ScopeResolver().resolve(parse_result, default_catalog="lake")
    assert model.relations[0].catalog == "lake"
    assert model.relations[0].schema == "ods"
    assert model.relations[0].table == "order_table"


def test_scope_resolver_select_items_keep_source_columns():
    parse_result = _parse("SELECT o.order_no AS no, 1 AS flag FROM order_table o")
    model, _ = ScopeResolver().resolve(parse_result)
    assert model.select_items[0].output_name == "no"
    assert model.select_items[0].source_columns[0].table == "o"
    assert model.select_items[0].source_columns[0].column == "order_no"
    assert model.select_items[1].expression_kind == "literal"


def test_scope_resolver_duplicate_alias_warns():
    parse_result = _parse("SELECT a.id FROM t1 a JOIN t2 a ON a.id = a.id")
    _, diagnostics = ScopeResolver().resolve(parse_result)
    assert any(d.code == DiagnosticCode.DUPLICATE_ALIAS for d in diagnostics)
