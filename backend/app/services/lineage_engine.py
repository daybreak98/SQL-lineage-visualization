"""P0 LineageIR generator."""

from __future__ import annotations

from app.domain.contracts import (
    ConfidenceLevel,
    EntityType,
    LineageEdge,
    LineageEdgeType,
    LineageIR,
    LineageNode,
    LineageNodeType,
    MetadataObjectRef,
    ScopeItem,
)
from app.domain.entity_id import EntityIdFactory
from app.domain.minimal_expression_model import ProjectionModel, ProjectionSourceRef
from app.domain.name_resolution_model import NameResolutionResult, ResolvedColumnRef
from app.domain.scope_model import ScopeModel


class LineageEngine:
    def build(
        self,
        scope_model: ScopeModel,
        name_resolution: NameResolutionResult,
        projection_model: ProjectionModel,
    ) -> LineageIR:
        nodes: dict[str, LineageNode] = {}
        edges: dict[str, LineageEdge] = {}
        resolved_lookup = {
            resolved.column_entity_id: resolved
            for resolved in name_resolution.resolved_columns
        }

        for relation in name_resolution.resolved_relations:
            nodes[relation.table_entity_id] = LineageNode(
                id=relation.table_entity_id,
                node_type=LineageNodeType.table,
                label=relation.table,
                entity_type=EntityType.table,
                metadata_ref=MetadataObjectRef(
                    catalog=relation.catalog,
                    schema=relation.schema,
                    table=relation.table,
                ),
                scope_id=scope_model.scope_id,
                comment=relation.table_row.get("comment"),
                attributes={"alias": relation.alias},
            )

        for projection in projection_model.projections:
            output_node = LineageNode(
                id=projection.output_entity_id,
                node_type=LineageNodeType.output_column,
                label=projection.output_name,
                entity_type=EntityType.output_column,
                scope_id=projection.scope_id,
                expression=projection.expression_sql,
                attributes={"ordinal": projection.ordinal},
            )
            nodes[output_node.id] = output_node

            if projection.literal_value is not None:
                literal_id = EntityIdFactory.literal(projection.scope_id, projection.ordinal)
                nodes[literal_id] = LineageNode(
                    id=literal_id,
                    node_type=LineageNodeType.expression,
                    label=projection.literal_value,
                    entity_type=EntityType.expression,
                    scope_id=projection.scope_id,
                    expression=projection.literal_value,
                    attributes={"kind": "literal"},
                )
                self._add_edge(edges, LineageEdgeType.projection, literal_id, output_node.id)
                continue

            if not projection.source_refs:
                unknown_id = EntityIdFactory.unknown(
                    projection.scope_id,
                    projection.output_name,
                    projection.ordinal,
                )
                nodes[unknown_id] = LineageNode(
                    id=unknown_id,
                    node_type=LineageNodeType.unknown,
                    label=projection.output_name,
                    entity_type=EntityType.unknown,
                    scope_id=projection.scope_id,
                    expression=projection.expression_sql,
                )
                self._add_edge(edges, LineageEdgeType.unknown, unknown_id, output_node.id)
                continue

            for source_ref in projection.source_refs:
                if source_ref.column_entity_id is None:
                    unknown_id = EntityIdFactory.unknown(
                        projection.scope_id,
                        source_ref.raw,
                        projection.ordinal,
                    )
                    nodes[unknown_id] = LineageNode(
                        id=unknown_id,
                        node_type=LineageNodeType.unknown,
                        label=source_ref.raw,
                        entity_type=EntityType.unknown,
                        scope_id=projection.scope_id,
                        attributes={"reason": source_ref.unresolved_reason or "unknown"},
                    )
                    self._add_edge(edges, LineageEdgeType.unknown, unknown_id, output_node.id)
                    continue

                resolved = resolved_lookup[source_ref.column_entity_id]
                self._ensure_column_node(nodes, resolved, scope_model.scope_id)
                edge_type = self._edge_type(projection.output_name, resolved)
                self._add_edge(edges, edge_type, resolved.column_entity_id, output_node.id)

        scope_item = ScopeItem(
            scope_id=scope_model.scope_id,
            scope_type=scope_model.scope_type,
            table_aliases={r.alias: r.table_entity_id for r in scope_model.relations},
        )
        partial = bool(name_resolution.unresolved_columns or projection_model.unsupported_expressions)
        return LineageIR(
            scopes=[scope_item],
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            partial=partial,
            confidence_level=ConfidenceLevel.medium if partial else ConfidenceLevel.high,
            confidence_reasons=(
                ["存在未知或不支持的字段/表达式，结果为 partial"] if partial else ["P0 字段级血缘完整解析"]
            ),
        )

    @staticmethod
    def _ensure_column_node(
        nodes: dict[str, LineageNode],
        resolved: ResolvedColumnRef,
        scope_id: str,
    ) -> None:
        table_node_id = resolved.table_entity_id
        if table_node_id not in nodes:
            nodes[table_node_id] = LineageNode(
                id=table_node_id,
                node_type=LineageNodeType.table,
                label=resolved.table,
                entity_type=EntityType.table,
                metadata_ref=MetadataObjectRef(
                    catalog=resolved.catalog,
                    schema=resolved.schema,
                    table=resolved.table,
                ),
                scope_id=scope_id,
            )
        nodes.setdefault(
            resolved.column_entity_id,
            LineageNode(
                id=resolved.column_entity_id,
                node_type=LineageNodeType.column,
                label=resolved.column,
                entity_type=EntityType.column,
                metadata_ref=MetadataObjectRef(
                    catalog=resolved.catalog,
                    schema=resolved.schema,
                    table=resolved.table,
                    column=resolved.column,
                ),
                scope_id=scope_id,
                data_type=resolved.data_type,
                comment=resolved.comment,
            ),
        )

    @staticmethod
    def _edge_type(output_name: str, resolved: ResolvedColumnRef) -> LineageEdgeType:
        if output_name.lower() != resolved.column.lower():
            return LineageEdgeType.alias
        return LineageEdgeType.projection

    @staticmethod
    def _add_edge(
        edges: dict[str, LineageEdge],
        edge_type: LineageEdgeType,
        source: str,
        target: str,
    ) -> None:
        edge_id = EntityIdFactory.edge(edge_type.value, source, target)
        edges.setdefault(
            edge_id,
            LineageEdge(
                id=edge_id,
                edge_type=edge_type,
                source=source,
                target=target,
                label=edge_type.value,
                confidence=1.0 if edge_type != LineageEdgeType.unknown else 0.3,
            ),
        )
