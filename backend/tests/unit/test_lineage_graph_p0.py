from app.repositories.metadata_repository import MetadataRepository
from app.services.graph_builder import GraphBuilder
from app.services.lineage_engine import LineageEngine
from app.services.metadata_service import MetadataService
from app.services.name_resolver import NameResolver
from app.services.projection_extractor import ProjectionExtractor
from app.services.scope_resolver import ScopeResolver
from app.services.sql_parse_service import SqlParseService


def _seed(repo: MetadataRepository) -> None:
    repo.create_metadata_version("v1")
    table_id = repo.upsert_table("v1", "default", "default", "order_table", "order_table")
    repo.upsert_columns(
        table_id,
        "v1",
        [
            {"column_name": "order_no", "normalized_column_name": "order_no", "data_type": "string", "ordinal": 1},
            {"column_name": "amount", "normalized_column_name": "amount", "data_type": "decimal", "ordinal": 2},
        ],
    )


def _pipeline(repo: MetadataRepository, sql: str):
    parsed, diagnostics = SqlParseService().parse(sql)
    assert parsed.success, diagnostics
    scope, scope_diagnostics = ScopeResolver().resolve(parsed)
    assert scope_diagnostics == []
    names, name_diagnostics = NameResolver(MetadataService(repo)).resolve(scope, metadata_version="v1")
    projections = ProjectionExtractor().extract(scope, names)
    lineage = LineageEngine().build(scope, names, projections)
    graph = GraphBuilder().build(lineage)
    return projections, lineage, graph, name_diagnostics


def test_projection_lineage_graph_simple_select(repo):
    _seed(repo)
    projections, lineage, graph, diagnostics = _pipeline(repo, "SELECT order_no FROM order_table")
    assert diagnostics == []
    assert projections.projections[0].output_name == "order_no"
    assert any(n.id == "column:default.order_table.order_no" for n in lineage.nodes)
    assert any(n.id.startswith("output_column:scope:root:1:order_no") for n in lineage.nodes)
    assert graph.nodes
    assert graph.edges[0].source == "column:default.order_table.order_no"


def test_alias_generates_alias_edge(repo):
    _seed(repo)
    _, lineage, _, diagnostics = _pipeline(repo, "SELECT order_no AS no FROM order_table")
    assert diagnostics == []
    assert lineage.edges[0].edge_type.value == "alias"


def test_literal_generates_expression_node(repo):
    _seed(repo)
    projections, lineage, graph, diagnostics = _pipeline(repo, "SELECT 1 AS flag FROM order_table")
    assert diagnostics == []
    assert projections.projections[0].literal_value == "1 AS flag"
    assert any(n.node_type.value == "expression" for n in lineage.nodes)
    assert any(e.target.startswith("output_column:scope:root:1:flag") for e in graph.edges)
