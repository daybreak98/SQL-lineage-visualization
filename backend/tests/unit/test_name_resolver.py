from app.domain.contracts import DiagnosticCode
from app.repositories.metadata_repository import MetadataRepository
from app.services.metadata_service import MetadataService
from app.services.name_resolver import NameResolver
from app.services.scope_resolver import ScopeResolver
from app.services.sql_parse_service import SqlParseService


def _seed(repo: MetadataRepository) -> None:
    repo.create_metadata_version("v1")
    order_id = repo.upsert_table("v1", "default", "default", "order_table", "order_table")
    repo.upsert_columns(
        order_id,
        "v1",
        [
            {"column_name": "order_no", "normalized_column_name": "order_no", "data_type": "string", "ordinal": 1},
            {"column_name": "user_id", "normalized_column_name": "user_id", "data_type": "bigint", "ordinal": 2},
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


def _scope(sql: str):
    parsed, _ = SqlParseService().parse(sql)
    return ScopeResolver().resolve(parsed)[0]


def test_name_resolver_resolves_qualified_columns(repo):
    _seed(repo)
    model = _scope("SELECT o.order_no, u.user_name FROM order_table o JOIN user_table u ON o.user_id = u.user_id")
    result, diagnostics = NameResolver(MetadataService(repo)).resolve(model, metadata_version="v1")
    assert diagnostics == []
    assert len(result.resolved_columns) == 2
    assert result.resolved_columns[0].column_entity_id == "column:default.default.order_table.order_no"


def test_name_resolver_unknown_table_is_error(repo):
    _seed(repo)
    model = _scope("SELECT x.id FROM missing_table x")
    result, diagnostics = NameResolver(MetadataService(repo)).resolve(model, metadata_version="v1")
    assert result.metadata_context.missing_tables[0].table == "missing_table"
    assert any(d.code == DiagnosticCode.UNKNOWN_TABLE for d in diagnostics)


def test_name_resolver_unknown_column_is_warning(repo):
    _seed(repo)
    model = _scope("SELECT o.missing_col FROM order_table o")
    result, diagnostics = NameResolver(MetadataService(repo)).resolve(model, metadata_version="v1")
    assert result.metadata_context.missing_columns[0].column == "missing_col"
    assert any(d.code == DiagnosticCode.UNKNOWN_COLUMN for d in diagnostics)


def test_name_resolver_ambiguous_unqualified_column(repo):
    _seed(repo)
    model = _scope("SELECT user_id FROM order_table o JOIN user_table u ON o.user_id = u.user_id")
    result, diagnostics = NameResolver(MetadataService(repo)).resolve(model, metadata_version="v1")
    assert result.metadata_context.ambiguous_columns[0].column == "user_id"
    assert any(d.code == DiagnosticCode.AMBIGUOUS_COLUMN for d in diagnostics)
