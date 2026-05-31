"""Build a stable GraphViewModel from LineageIR."""

from __future__ import annotations

from app.domain.contracts import (
    GraphEdge,
    GraphEdgeType,
    GraphNode,
    GraphNodeType,
    GraphPosition,
    GraphViewMode,
    GraphViewModel,
    LineageEdge,
    LineageEdgeType,
    LineageIR,
    LineageNode,
    LineageNodeType,
)


class GraphBuilder:
    def build(self, lineage_ir: LineageIR) -> GraphViewModel:
        nodes = [
            self._node(lineage_node, index)
            for index, lineage_node in enumerate(lineage_ir.nodes)
        ]
        edges = [self._edge(edge) for edge in lineage_ir.edges]
        return GraphViewModel(
            view_mode=GraphViewMode.column,
            supported_view_modes=[GraphViewMode.table, GraphViewMode.column],
            nodes=nodes,
            edges=edges,
        )

    def _node(self, node: LineageNode, index: int) -> GraphNode:
        node_type = self._node_type(node)
        x = self._x(node.node_type)
        y = 72 + index * 58
        return GraphNode(
            id=node.id,
            entity_id=node.id,
            node_type=node_type,
            label=node.label,
            position=GraphPosition(x=x, y=y),
            source_location_id=node.source_location_id,
            data={
                "entity_type": node.entity_type.value,
                "scope_id": node.scope_id,
                "metadata_ref": node.metadata_ref.model_dump() if node.metadata_ref else None,
                "data_type": node.data_type,
                "comment": node.comment,
                "expression": node.expression,
                **node.attributes,
            },
        )

    @staticmethod
    def _edge(edge: LineageEdge) -> GraphEdge:
        return GraphEdge(
            id=edge.id,
            edge_type=GraphBuilder._edge_type(edge.edge_type),
            source=edge.source,
            target=edge.target,
            source_entity_id=edge.source,
            target_entity_id=edge.target,
            label=edge.label,
            source_location_id=edge.source_location_id,
            data=edge.attributes,
        )

    @staticmethod
    def _node_type(node: LineageNode) -> GraphNodeType:
        mapping = {
            LineageNodeType.table: GraphNodeType.table,
            LineageNodeType.column: GraphNodeType.column,
            LineageNodeType.output_column: GraphNodeType.output_column,
            LineageNodeType.expression: GraphNodeType.expression,
            LineageNodeType.unknown: GraphNodeType.unknown,
        }
        return mapping.get(node.node_type, GraphNodeType.unknown)

    @staticmethod
    def _edge_type(edge_type: LineageEdgeType) -> GraphEdgeType:
        mapping = {
            LineageEdgeType.projection: GraphEdgeType.projection,
            LineageEdgeType.alias: GraphEdgeType.alias,
            LineageEdgeType.expression: GraphEdgeType.expression,
            LineageEdgeType.filter_condition: GraphEdgeType.filter_condition,
            LineageEdgeType.unknown: GraphEdgeType.unknown,
        }
        return mapping.get(edge_type, GraphEdgeType.unknown)

    @staticmethod
    def _x(node_type: LineageNodeType) -> int:
        if node_type == LineageNodeType.table:
            return 48
        if node_type == LineageNodeType.column:
            return 270
        if node_type == LineageNodeType.output_column:
            return 560
        return 160
