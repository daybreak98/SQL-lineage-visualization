"""P0+M23 LineageIR generator with CTE internal edges, join condition edges,
union mapping edges, and expression-aware edges (aggregate / CASE WHEN / window)."""

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
from app.domain.expression_model import ExpressionModel
from app.domain.minimal_expression_model import ProjectionModel, ProjectionSourceRef
from app.domain.name_resolution_model import NameResolutionResult, ResolvedColumnRef
from app.domain.scope_model import ColumnReference, ScopeModel


class LineageEngine:
    def build(
        self,
        scope_model: ScopeModel,
        name_resolution: NameResolutionResult,
        projection_model: ProjectionModel,
        *,
        expression_model: ExpressionModel | None = None,
    ) -> LineageIR:
        nodes: dict[str, LineageNode] = {}
        edges: dict[str, LineageEdge] = {}
        resolved_lookup = {
            resolved.column_entity_id: resolved
            for resolved in name_resolution.resolved_columns
        }
        trace_context = self._build_trace_context(scope_model)

        # ── M23 (R13a): build expression lookup by (scope_id, ordinal) ──
        expression_by_key: dict[tuple[str, int], list] = {}
        if expression_model:
            for agg in expression_model.aggregates:
                expression_by_key.setdefault((agg.scope_id, agg.ordinal), []).append(agg)
            for cw in expression_model.case_whens:
                expression_by_key.setdefault((cw.scope_id, cw.ordinal), []).append(cw)
            for wf in expression_model.window_functions:
                expression_by_key.setdefault((wf.scope_id, wf.ordinal), []).append(wf)

        # 表级血缘：从 scope_model.relations 获取所有物理表（不依赖元数据）
        # CTE/子查询在表级视图中不展示，只保留物理表
        resolved_entity_ids = {r.table_entity_id for r in name_resolution.resolved_relations}
        for relation in scope_model.relations:
            if relation.is_cte:
                continue
            label = relation.table
            if relation.schema and relation.schema != "default":
                label = f"{relation.schema}.{relation.table}"
            nodes[relation.table_entity_id] = LineageNode(
                id=relation.table_entity_id,
                node_type=LineageNodeType.table,
                label=label,
                entity_type=EntityType.table,
                metadata_ref=MetadataObjectRef(
                    catalog=relation.catalog,
                    schema=relation.schema,
                    table=relation.table,
                ),
                scope_id=scope_model.scope_id,
                comment="元数据未导入" if relation.table_entity_id not in resolved_entity_ids else None,
                attributes={"alias": relation.alias},
            )

        # ── P2: CTE 子查询节点（子查询级血缘展示）──
        for relation in scope_model.relations:
            if not relation.is_cte:
                continue
            cte_label = relation.alias or relation.table
            nodes[relation.table_entity_id] = LineageNode(
                id=relation.table_entity_id,
                node_type=LineageNodeType.cte,
                label=cte_label,
                entity_type=EntityType.cte,
                scope_id=scope_model.scope_id,
                attributes={"alias": relation.alias, "is_cte": True,
                           "source_name": relation.source_name},
            )

        # ── CTE 依赖边 ──
        # Build CTE → CTE edges based on CTE body references
        cte_entities = {r.table_entity_id for r in scope_model.relations if r.is_cte}
        for cte_name, columns in scope_model.cte_columns.items():
            cte_rel = next((r for r in scope_model.relations if r.is_cte and r.table.lower() == cte_name), None)
            if not cte_rel:
                continue
            # Find which tables/CTEs are referenced in the CTE body
            for icol in columns:
                for src_col in icol.source_columns:
                    src_table = src_col.table or ""
                    # Check if source references a physical table or another CTE
                    for rel in scope_model.relations:
                        if rel.alias and src_table.lower() == rel.alias.lower():
                            edge_type = LineageEdgeType.projection if not rel.is_cte else LineageEdgeType.projection
                            self._add_edge(edges, edge_type, rel.table_entity_id, cte_rel.table_entity_id)
                        elif not rel.is_cte and src_table.lower() == rel.table.lower():
                            self._add_edge(edges, LineageEdgeType.projection, rel.table_entity_id, cte_rel.table_entity_id)

        # ── M19 增强: Join 条件边 ──
        for jk in scope_model.join_keys:
            # Resolve left and right columns from name resolution
            left_label = jk.left.raw
            right_label = jk.right.raw
            # Try to find resolved column IDs for join key columns
            left_id = self._find_column_id(jk.left, resolved_lookup)
            right_id = self._find_column_id(jk.right, resolved_lookup)
            if left_id and right_id:
                self._add_edge(
                    edges, LineageEdgeType.join_condition,
                    left_id, right_id,
                    label=f"ON {left_label} = {right_label}",
                )
            elif left_id and right_id is None:
                # Create unknown node for unresolved right column
                right_unknown_id = EntityIdFactory.unknown(
                    scope_model.scope_id, jk.right.column, 0,
                )
                nodes.setdefault(
                    right_unknown_id,
                    LineageNode(
                        id=right_unknown_id,
                        node_type=LineageNodeType.unknown,
                        label=jk.right.column,
                        entity_type=EntityType.unknown,
                        scope_id=scope_model.scope_id,
                    ),
                )
                self._add_edge(
                    edges, LineageEdgeType.join_condition,
                    left_id, right_unknown_id,
                    label=f"ON {left_label} = {right_label}",
                )

        # ── M19 增强: UNION mapping 边 ──
        for segment in scope_model.union_segments:
            for si in segment.select_items:
                # For each segment's select item, find the corresponding root output column
                root_output_id = EntityIdFactory.output_column(
                    scope_model.scope_id, si.output_name, si.ordinal,
                )
                # Create source column nodes for the segment
                for src_ref in si.source_columns:
                    resolved = resolved_lookup.get(
                        EntityIdFactory.column("default", "default", src_ref.table or "unknown", src_ref.column),
                    )
                    if resolved:
                        self._ensure_column_node(nodes, resolved, scope_model.scope_id)
                        self._add_edge(
                            edges, LineageEdgeType.union_mapping,
                            resolved.column_entity_id, root_output_id,
                            label=f"UNION segment {segment.segment_index}",
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

            # ── M23 (R13a): expression-aware edges ──
            expr_key = (projection.scope_id, projection.ordinal)
            if expr_key in expression_by_key:
                self._add_expression_edges(
                    nodes, edges, expression_by_key[expr_key],
                    output_node.id, resolved_lookup,
                    projection.scope_id, scope_model.scope_id,
                    scope_model, trace_context,
                )
                continue

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
                traced_sources = self._trace_projection_source(
                    source_ref, scope_model, trace_context,
                )
                if traced_sources:
                    for traced in traced_sources:
                        self._ensure_column_node(nodes, traced, scope_model.scope_id)
                        edge_type = self._edge_type(projection.output_name, traced)
                        self._add_edge(edges, edge_type, traced.column_entity_id, output_node.id)
                    continue

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

        scopes: list[ScopeItem] = []
        scopes.append(ScopeItem(
            scope_id=scope_model.scope_id,
            scope_type=scope_model.scope_type,
            table_aliases={r.alias: r.table_entity_id for r in scope_model.relations},
        ))
        # Add CTE child scopes
        for relation in scope_model.relations:
            if relation.is_cte:
                cte_id = f"scope:cte:{relation.table}"
                cte_aliases: dict[str, str] = {}
                # Map CTE body references to source entities
                cte_cols = scope_model.cte_columns.get(relation.table.lower(), [])
                for col in cte_cols:
                    for src in col.source_columns:
                        if src.table:
                            for r in scope_model.relations:
                                if r.alias and src.table.lower() == r.alias.lower():
                                    cte_aliases.setdefault(src.table, r.table_entity_id)
                scopes.append(ScopeItem(
                    scope_id=cte_id,
                    parent_scope_id=scope_model.scope_id,
                    scope_type="cte",
                    table_aliases=cte_aliases,
                ))
        partial = bool(name_resolution.unresolved_columns or projection_model.unsupported_expressions)
        return LineageIR(
            scopes=scopes,
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            partial=partial,
            confidence_level=ConfidenceLevel.medium if partial else ConfidenceLevel.high,
            confidence_reasons=(
                ["存在未知或不支持的字段/表达式，结果为 partial"] if partial else ["P0+M19 字段级血缘完整解析"]
            ),
        )

    # ── M23 (R13a): expression edge helpers ──

    def _add_expression_edges(
        self,
        nodes: dict[str, LineageNode],
        edges: dict[str, LineageEdge],
        expr_items: list,
        output_node_id: str,
        resolved_lookup: dict[str, ResolvedColumnRef],
        scope_id: str,
        root_scope_id: str,
        scope_model: ScopeModel,
        trace_context: dict,
    ) -> None:
        """Create expression nodes and edges for aggregate / CASE WHEN / window functions."""
        for item in expr_items:
            # Determine label and type
            if hasattr(item, "function_name"):
                if hasattr(item, "partition_by_columns"):
                    # WindowFunction
                    label = f"{item.function_name}() OVER (...)"
                    kind = "window"
                else:
                    # AggregateExpression
                    label = f"{item.function_name}({item.args_sql or ''})"
                    kind = "aggregate"
            else:
                # CaseWhenExpression
                label = f"CASE WHEN {item.branches[0].condition_sql if item.branches else '...'} ... END"
                kind = "case_when"

            expr_node = LineageNode(
                id=item.expression_id,
                node_type=LineageNodeType.expression,
                label=label,
                entity_type=EntityType.expression,
                scope_id=scope_id,
                expression=item.expression_sql,
                attributes={"kind": kind},
            )
            nodes[expr_node.id] = expr_node

            # Edge: expression node → output column
            self._add_edge(
                edges, LineageEdgeType.expression,
                expr_node.id, output_node_id,
                label=f"{kind} → output",
            )

            # Collect all source columns from the expression item
            source_cols: list = getattr(item, "source_columns", [])
            if hasattr(item, "partition_by_columns"):
                source_cols = list(source_cols)  # copy
                for pc in item.partition_by_columns:
                    if pc not in source_cols:
                        source_cols.append(pc)
                for oc in item.order_by_columns:
                    if oc not in source_cols:
                        source_cols.append(oc)

            # For each source column, resolve to a node and create edge
            for col_ref in source_cols:
                traced_sources = self._trace_column_reference(
                    col_ref, None, scope_model, trace_context,
                )
                if traced_sources:
                    for traced in traced_sources:
                        self._ensure_column_node(nodes, traced, root_scope_id)
                        self._add_edge(
                            edges, LineageEdgeType.expression,
                            traced.column_entity_id, expr_node.id,
                            label=col_ref.raw,
                        )
                    continue

                col_entity_id = self._resolve_column_id(col_ref, resolved_lookup)
                if col_entity_id:
                    resolved = resolved_lookup.get(col_entity_id)
                    if resolved:
                        self._ensure_column_node(nodes, resolved, root_scope_id)
                    self._add_edge(
                        edges, LineageEdgeType.expression,
                        col_entity_id, expr_node.id,
                        label=col_ref.raw,
                    )
                else:
                    # Unresolved source column
                    unknown_id = EntityIdFactory.unknown(
                        root_scope_id, col_ref.raw, 0,
                    )
                    nodes.setdefault(
                        unknown_id,
                        LineageNode(
                            id=unknown_id,
                            node_type=LineageNodeType.unknown,
                            label=col_ref.raw,
                            entity_type=EntityType.unknown,
                            scope_id=root_scope_id,
                        ),
                    )
                    self._add_edge(
                        edges, LineageEdgeType.unknown,
                        unknown_id, expr_node.id,
                        label=col_ref.raw,
                    )

    def _build_trace_context(self, scope_model: ScopeModel) -> dict:
        cte_relations = [r for r in scope_model.relations if r.is_cte]
        physical_relations = [r for r in scope_model.relations if not r.is_cte]
        return {
            "cte_relations": cte_relations,
            "physical_relations": physical_relations,
            "cte_columns": {
                name.lower(): {col.output_name.lower(): col for col in cols}
                for name, cols in scope_model.cte_columns.items()
            },
            "cte_source_names": {
                name.lower(): [source.lower() for source in sources]
                for name, sources in scope_model.cte_source_names.items()
            },
        }

    def _trace_projection_source(
        self,
        source_ref: ProjectionSourceRef,
        scope_model: ScopeModel,
        trace_context: dict,
    ) -> list[ResolvedColumnRef]:
        if source_ref.unresolved_reason and source_ref.unresolved_reason != "ambiguous":
            return []
        if not source_ref.column:
            return []
        ref = ColumnReference(
            raw=source_ref.raw,
            table=source_ref.table,
            column=source_ref.column,
        )
        current_scope = "__root__" if "__root__" in trace_context["cte_source_names"] else None
        return self._trace_column_reference(ref, current_scope, scope_model, trace_context)

    def _trace_column_reference(
        self,
        reference: ColumnReference,
        current_cte: str | None,
        scope_model: ScopeModel,
        trace_context: dict,
        visited: set[tuple[str, str]] | None = None,
    ) -> list[ResolvedColumnRef]:
        visited = visited or set()
        col = reference.column.lower()
        table = reference.table.lower() if reference.table else None

        if table:
            cte_matches = self._matching_cte_relations(table, trace_context, current_cte)
            if cte_matches:
                traced: list[ResolvedColumnRef] = []
                for relation in cte_matches:
                    traced.extend(self._trace_cte_column(
                        relation.table, col, scope_model, trace_context, visited,
                    ))
                if traced:
                    return self._dedupe_resolved(traced)

            physical = self._matching_physical_relations(table, trace_context, current_cte)
            if physical:
                return [
                    self._synthetic_column_ref(reference, relation, reference.column)
                    for relation in physical
                ]

        # `table` may be a subquery alias, or the column may be unqualified.
        # In that case, search the CTEs that feed the current CTE first.
        allowed_sources = self._allowed_source_names(current_cte, trace_context)
        traced = self._trace_named_cte_sources(
            col, allowed_sources, scope_model, trace_context, visited,
        )
        if traced:
            return traced

        physical_sources = self._physical_sources_for_context(current_cte, trace_context)
        if physical_sources:
            # For unqualified columns inside a CTE, prefer the primary FROM
            # relation. Joined table columns are normally qualified and handled
            # above; returning every joined table creates noisy false positives.
            return [self._synthetic_column_ref(reference, physical_sources[0], reference.column)]

        return []

    def _trace_cte_column(
        self,
        cte_name: str,
        column: str,
        scope_model: ScopeModel,
        trace_context: dict,
        visited: set[tuple[str, str]],
    ) -> list[ResolvedColumnRef]:
        key = (cte_name.lower(), column.lower())
        if key in visited:
            return []
        visited = set(visited)
        visited.add(key)

        cte_columns = trace_context["cte_columns"].get(cte_name.lower(), {})
        cte_col = cte_columns.get(column.lower())
        if cte_col is None:
            return []

        if not cte_col.source_columns:
            return []

        traced: list[ResolvedColumnRef] = []
        for source in cte_col.source_columns:
            traced.extend(self._trace_column_reference(
                source, cte_name, scope_model, trace_context, visited,
            ))
        return self._dedupe_resolved(traced)

    @staticmethod
    def _allowed_source_names(current_cte: str | None, trace_context: dict) -> list[str]:
        if not current_cte:
            return []
        return trace_context["cte_source_names"].get(current_cte.lower(), [])

    def _matching_cte_relations(
        self,
        table_or_alias: str,
        trace_context: dict,
        current_cte: str | None,
    ) -> list:
        allowed = set(self._allowed_source_names(current_cte, trace_context))
        matches = [
            relation for relation in trace_context["cte_relations"]
            if relation.alias.lower() == table_or_alias or relation.table.lower() == table_or_alias
        ]
        if allowed:
            preferred = [relation for relation in matches if relation.table.lower() in allowed]
            if preferred:
                return preferred
        return matches

    def _matching_physical_relations(
        self,
        table_or_alias: str,
        trace_context: dict,
        current_cte: str | None,
    ) -> list:
        allowed = set(self._allowed_source_names(current_cte, trace_context))
        matches = [
            relation for relation in trace_context["physical_relations"]
            if relation.alias.lower() == table_or_alias or relation.table.lower() == table_or_alias
        ]
        if allowed:
            preferred = [relation for relation in matches if relation.table.lower() in allowed]
            if preferred:
                return preferred
        # Avoid cross-CTE alias collisions such as `a` reused in multiple CTEs.
        if current_cte and len(matches) > 1:
            return []
        return matches

    def _trace_named_cte_sources(
        self,
        column: str,
        allowed_sources: list[str],
        scope_model: ScopeModel,
        trace_context: dict,
        visited: set[tuple[str, str]],
    ) -> list[ResolvedColumnRef]:
        source_names = allowed_sources or list(trace_context["cte_columns"].keys())
        traced: list[ResolvedColumnRef] = []
        for source_name in source_names:
            if column not in trace_context["cte_columns"].get(source_name, {}):
                continue
            traced.extend(self._trace_cte_column(
                source_name, column, scope_model, trace_context, visited,
            ))
        return self._dedupe_resolved(traced)

    def _physical_sources_for_context(self, current_cte: str | None, trace_context: dict) -> list:
        allowed = set(self._allowed_source_names(current_cte, trace_context))
        if not allowed:
            return []
        return [
            relation for relation in trace_context["physical_relations"]
            if relation.table.lower() in allowed
        ]

    @staticmethod
    def _synthetic_column_ref(
        reference: ColumnReference,
        relation,
        column: str,
    ) -> ResolvedColumnRef:
        return ResolvedColumnRef(
            reference=reference,
            relation_id=relation.relation_id,
            column_entity_id=EntityIdFactory.column(
                relation.catalog, relation.schema, relation.table, column,
            ),
            table_entity_id=relation.table_entity_id,
            catalog=relation.catalog,
            schema=relation.schema,
            table=relation.table,
            column=column,
            data_type=None,
            comment=None,
        )

    @staticmethod
    def _dedupe_resolved(items: list[ResolvedColumnRef]) -> list[ResolvedColumnRef]:
        deduped: dict[str, ResolvedColumnRef] = {}
        for item in items:
            deduped.setdefault(item.column_entity_id, item)
        return list(deduped.values())

    @staticmethod
    def _resolve_column_id(
        col_ref,
        resolved_lookup: dict[str, ResolvedColumnRef],
    ) -> str | None:
        """Match a ColumnReference to a resolved column entity ID."""
        if not col_ref.column:
            return None
        col_lower = col_ref.column.lower()
        table_lower = col_ref.table.lower() if col_ref.table else None
        for entity_id, resolved in resolved_lookup.items():
            if resolved.column.lower() != col_lower:
                continue
            if table_lower:
                ref = resolved.reference
                if ref.table and ref.table.lower() == table_lower:
                    return entity_id
                if resolved.table.lower() == table_lower:
                    return entity_id
            # If no table in col_ref, match by column name only
            return entity_id
        return None

    @staticmethod
    def _find_column_id(
        col_ref,
        resolved_lookup: dict[str, ResolvedColumnRef],
    ) -> str | None:
        """Find the resolved column_entity_id for a ColumnReference by matching column name.
        
        The col_ref.table is typically a table alias from the ON clause.
        We match against resolved columns by column name and check the reference's table field."""
        if not col_ref.column or not col_ref.table:
            return None
        col_lower = col_ref.column.lower()
        table_lower = col_ref.table.lower()
        for entity_id, resolved in resolved_lookup.items():
            if resolved.column.lower() != col_lower:
                continue
            # Check if the resolved reference points to the same table/alias
            ref = resolved.reference
            if ref.table and ref.table.lower() == table_lower:
                return entity_id
            if resolved.table.lower() == table_lower:
                return entity_id
        return None

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
        label: str | None = None,
    ) -> None:
        edge_id = EntityIdFactory.edge(edge_type.value, source, target)
        edges.setdefault(
            edge_id,
            LineageEdge(
                id=edge_id,
                edge_type=edge_type,
                source=source,
                target=target,
                label=label or edge_type.value,
                confidence=1.0 if edge_type != LineageEdgeType.unknown else 0.3,
            ),
        )
