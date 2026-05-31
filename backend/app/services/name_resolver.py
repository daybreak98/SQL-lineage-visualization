"""P0+M19 NameResolver: resolve scope columns against imported metadata.

增强:
- CTE 字段回溯：CTE 输出字段追溯到 CTE 体内部原始字段
- Join 消歧：多表同名字段出现在 JOIN 中时，结合 ON 子句字段归属判断
- Union 多来源字段合并：同名输出字段标记为 union_mapping
"""

from __future__ import annotations

from app.diagnostics.collector import DiagnosticsCollector
from app.domain.contracts import (
    AmbiguousColumn,
    Diagnostic,
    DiagnosticCode,
    DiagnosticLevel,
    MetadataContext,
    MissingColumn,
    MissingTable,
    ResolvedTable,
)
from app.domain.entity_id import EntityIdFactory, normalize_name
from app.domain.name_resolution_model import (
    NameResolutionResult,
    ResolvedColumnRef,
    ResolvedRelation,
    UnresolvedColumnRef,
)
from app.domain.scope_model import ColumnReference, CteInternalColumn, ScopeModel, ScopeRelation
from app.services.metadata_service import MetadataService


class NameResolver:
    def __init__(self, metadata_service: MetadataService):
        self.metadata_service = metadata_service

    def resolve(
        self,
        scope_model: ScopeModel,
        *,
        metadata_version: str = "latest",
        default_catalog: str = "default",
        default_schema: str = "default",
        case_sensitive: bool = False,
    ) -> tuple[NameResolutionResult, list[Diagnostic]]:
        collector = DiagnosticsCollector()
        effective_version = self.metadata_service.effective_version(metadata_version)
        resolved_relations: list[ResolvedRelation] = []
        missing_tables: list[MissingTable] = []
        missing_relation_ids: set[str] = set()

        for relation in scope_model.relations:
            # CTE 表：WITH 子句中定义的临时表，查 CTE 内部列信息
            if relation.is_cte:
                cte_columns = self._get_cte_columns_for_relation(relation, scope_model)
                resolved_relations.append(
                    ResolvedRelation(
                        relation_id=relation.relation_id,
                        alias=relation.alias,
                        catalog=relation.catalog,
                        schema=relation.schema,
                        table=relation.table,
                        table_entity_id=relation.table_entity_id,
                        table_row={
                            "table_name": relation.table,
                            "comment": "CTE 临时表",
                            "cte_columns_count": len(cte_columns),
                        },
                        columns=cte_columns,
                        is_cte=True,
                    )
                )
                continue

            table = self.metadata_service.get_table(
                metadata_version=metadata_version,
                catalog=relation.catalog,
                schema=relation.schema,
                table=relation.table,
            )
            if table is None:
                missing_relation_ids.add(relation.relation_id)
                missing_tables.append(
                    MissingTable(
                        catalog=relation.catalog,
                        schema=relation.schema,
                        table=relation.table,
                        alias=relation.alias,
                    )
                )
                collector.add(
                    DiagnosticCode.UNKNOWN_TABLE,
                    DiagnosticLevel.warning,
                    f"元数据中找不到表: {relation.catalog}.{relation.schema}.{relation.table}",
                    suggestion="请先导入对应表元数据，或检查 SQL 中的 catalog/schema/table",
                    related_entity_ids=[relation.table_entity_id],
                    details={
                        "catalog": relation.catalog,
                        "schema": relation.schema,
                        "table": relation.table,
                        "alias": relation.alias,
                    },
                )
                continue
            columns = self.metadata_service.get_columns(table, metadata_version=metadata_version)
            resolved_relations.append(
                ResolvedRelation(
                    relation_id=relation.relation_id,
                    alias=relation.alias,
                    catalog=relation.catalog,
                    schema=relation.schema,
                    table=relation.table,
                    table_entity_id=relation.table_entity_id,
                    table_row=table,
                    columns=columns,
                )
            )

        resolved_columns: list[ResolvedColumnRef] = []
        unresolved_columns: list[UnresolvedColumnRef] = []
        missing_columns: list[MissingColumn] = []
        ambiguous_columns: list[AmbiguousColumn] = []

        for item in scope_model.select_items:
            for reference in item.source_columns:
                if not reference.table and missing_tables and not resolved_relations:
                    continue
                if self._references_missing_relation(
                    reference,
                    scope_model.relations,
                    missing_relation_ids,
                    case_sensitive=case_sensitive,
                ):
                    continue

                # CTE 列引用：支持字段回溯（M19 增强）
                if self._references_cte_relation(
                    reference,
                    scope_model.relations,
                    case_sensitive=case_sensitive,
                ):
                    cte_trace = self._trace_cte_column(
                        reference, scope_model, resolved_relations,
                        case_sensitive=case_sensitive,
                    )
                    if cte_trace is not None:
                        resolved_columns.append(cte_trace)
                    # 如果 trace 失败，仍视为已解析（CTE 列默认有效）
                    continue

                matches = self._resolve_reference(
                    reference,
                    scope_model.relations,
                    resolved_relations,
                    case_sensitive=case_sensitive,
                )
                if len(matches) == 1:
                    # M19 增强: 如果唯一匹配来自 CTE，尝试回溯到物理表
                    traced = self._maybe_trace_single_cte_match(
                        matches[0], scope_model, resolved_relations,
                        case_sensitive=case_sensitive,
                    )
                    if traced is not None:
                        resolved_columns.append(traced)
                    else:
                        resolved_columns.append(matches[0])
                    continue

                if len(matches) > 1:
                    # M19 增强: CTE 去重——当匹配包含 CTE 时，尝试回溯到物理表
                    dedup_matches = self._dedup_cte_matches(
                        reference, matches, scope_model, resolved_relations,
                        case_sensitive=case_sensitive,
                    )
                    if len(dedup_matches) == 1:
                        resolved_columns.append(dedup_matches[0])
                        continue

                    # M19 增强: Join 消歧
                    disambiguated = self._join_disambiguate(
                        reference, matches, scope_model, case_sensitive=case_sensitive,
                    )
                    if disambiguated is not None:
                        resolved_columns.append(disambiguated)
                        continue

                    candidates = [m.column_entity_id for m in matches]
                    unresolved_columns.append(
                        UnresolvedColumnRef(
                            reference=reference,
                            reason="ambiguous",
                            candidate_columns=candidates,
                        )
                    )
                    ambiguous_columns.append(
                        AmbiguousColumn(
                            column=reference.column,
                            scope_id=scope_model.scope_id,
                            candidate_columns=candidates,
                        )
                    )
                    collector.add(
                        DiagnosticCode.AMBIGUOUS_COLUMN,
                        DiagnosticLevel.warning,
                        f"字段引用存在歧义: {reference.raw}",
                        suggestion="请使用表别名限定字段来源",
                        related_entity_ids=candidates,
                        details={"column": reference.column, "candidates": candidates},
                    )
                    continue

                # 如果列引用指向 CTE 表但没有列匹配 → 不要报告 UNKNOWN_COLUMN
                if reference.table and self._references_cte_relation(
                    reference,
                    scope_model.relations,
                    case_sensitive=case_sensitive,
                ):
                    continue

                candidate_tables = [r.table_entity_id for r in resolved_relations]
                unresolved_columns.append(
                    UnresolvedColumnRef(
                        reference=reference,
                        reason="unknown",
                        candidate_columns=[],
                    )
                )
                missing_columns.append(
                    MissingColumn(
                        column=reference.column,
                        scope_id=scope_model.scope_id,
                        candidate_tables=candidate_tables,
                    )
                )
                collector.add(
                    DiagnosticCode.UNKNOWN_COLUMN,
                    DiagnosticLevel.warning,
                    f"元数据中找不到字段: {reference.raw}",
                    suggestion="请检查字段名或补充元数据；多表查询建议使用表别名",
                    related_entity_ids=candidate_tables,
                    details={"column": reference.column, "table": reference.table},
                )

        # M19 增强: UNION 多来源字段合并
        if scope_model.union_segments:
            union_resolved, union_unresolved = self._resolve_union_columns(
                scope_model, resolved_relations, case_sensitive=case_sensitive,
            )
            resolved_columns.extend(union_resolved)
            unresolved_columns.extend(union_unresolved)

        context = MetadataContext(
            metadata_version=effective_version,
            case_sensitive=case_sensitive,
            default_catalog=default_catalog,
            default_schema=default_schema,
            resolved_tables=[
                ResolvedTable(
                    entity_id=relation.table_entity_id,
                    catalog=relation.catalog,
                    schema=relation.schema,
                    table=relation.table,
                    alias=relation.alias,
                    columns=[c["column_name"] for c in relation.columns],
                )
                for relation in resolved_relations
            ],
            missing_tables=missing_tables,
            missing_columns=missing_columns,
            ambiguous_columns=ambiguous_columns,
        )
        return (
            NameResolutionResult(
                metadata_context=context,
                resolved_relations=resolved_relations,
                resolved_columns=resolved_columns,
                unresolved_columns=unresolved_columns,
            ),
            collector.list(),
        )

    # ── M19: 单匹配 CTE 回溯 ──
    def _maybe_trace_single_cte_match(
        self,
        match: ResolvedColumnRef,
        scope_model: ScopeModel,
        resolved_relations: list[ResolvedRelation],
        case_sensitive: bool,
    ) -> ResolvedColumnRef | None:
        """If the single match is from a CTE, attempt to trace back to the
        physical source column. Returns the traced ResolvedColumnRef or None
        if trace is not possible (caller should use original match)."""
        if not self._is_cte_match(match, scope_model.relations, case_sensitive=case_sensitive):
            return None
        return self._trace_cte_column_from_match(
            match, scope_model, resolved_relations, case_sensitive=case_sensitive,
        )

    # ── M19: CTE 去重 ──
    def _dedup_cte_matches(
        self,
        reference: ColumnReference,
        matches: list[ResolvedColumnRef],
        scope_model: ScopeModel,
        resolved_relations: list[ResolvedRelation],
        *,
        case_sensitive: bool,
    ) -> list[ResolvedColumnRef]:
        """When multi-matches include CTE relations, trace CTE columns back to
        their physical sources and deduplicate.

        Example: SELECT user_id FROM mt (where mt is a CTE selecting user_id
        FROM order_table). Both mt and order_table match user_id, but mt's
        source is order_table, so we can deduplicate to order_table."""
        # Separate CTE matches from physical matches
        cte_matches: list[ResolvedColumnRef] = []
        physical_matches: list[ResolvedColumnRef] = []
        for m in matches:
            if self._is_cte_match(m, scope_model.relations, case_sensitive=case_sensitive):
                cte_matches.append(m)
            else:
                physical_matches.append(m)

        if not cte_matches:
            return matches  # No CTE matches, return as-is

        # For each CTE match, attempt traceback to physical column
        traced_ids: set[str] = set()
        for cte_match in cte_matches:
            trace = self._trace_cte_column_from_match(
                cte_match, scope_model, resolved_relations, case_sensitive=case_sensitive,
            )
            if trace is not None:
                traced_ids.add(trace.column_entity_id)

        # Deduplicated physical matches (only keep those not already traced)
        result: list[ResolvedColumnRef] = []
        seen_ids: set[str] = traced_ids.copy()
        for pm in physical_matches:
            if pm.column_entity_id not in seen_ids:
                result.append(pm)
                seen_ids.add(pm.column_entity_id)

        # Add traced CTE columns as physical matches
        for tid in traced_ids:
            # Find the corresponding ResolvedColumnRef from physical matches or create new
            found = next((pm for pm in physical_matches if pm.column_entity_id == tid), None)
            if found:
                result.append(found)
            # If no physical match with this ID, we can't create one here - skip

        if not result:
            return matches  # If dedup eliminated everything, return original

        return result

    def _is_cte_match(
        self,
        match: ResolvedColumnRef,
        scope_relations: list[ScopeRelation],
        case_sensitive: bool,
    ) -> bool:
        """Check if a resolved column match comes from a CTE relation."""
        for relation in scope_relations:
            if not relation.is_cte:
                continue
            if normalize_name(relation.alias, case_sensitive=case_sensitive) == \
               normalize_name(match.table, case_sensitive=case_sensitive):
                return True
            if normalize_name(relation.table, case_sensitive=case_sensitive) == \
               normalize_name(match.table, case_sensitive=case_sensitive):
                return True
        # Also check using catalog "cte"
        if match.catalog == "cte":
            return True
        return False

    def _trace_cte_column_from_match(
        self,
        cte_match: ResolvedColumnRef,
        scope_model: ScopeModel,
        resolved_relations: list[ResolvedRelation],
        case_sensitive: bool,
        _depth: int = 0,
    ) -> ResolvedColumnRef | None:
        """Given a ResolvedColumnRef that belongs to a CTE, trace it back to the
        underlying physical table's column."""
        if _depth > 10:  # 防止无限递归
            return None
        # Find the CTE name from the match
        cte_name = cte_match.table.lower()
        internal_columns = scope_model.cte_columns.get(cte_name, [])
        col_name = normalize_name(cte_match.column, case_sensitive=case_sensitive)

        # Find matching CTE internal column
        for icol in internal_columns:
            if normalize_name(icol.output_name, case_sensitive=case_sensitive) != col_name:
                continue
            # Found the CTE internal column - trace its source
            for src_col in icol.source_columns:
                src_col_name = normalize_name(src_col.column, case_sensitive=case_sensitive)
                for resolved_rel in resolved_relations:
                    if resolved_rel.is_cte:
                        continue
                    # If source column has a table qualifier, check it matches
                    if src_col.table:
                        src_table = normalize_name(src_col.table, case_sensitive=case_sensitive)
                        rel_alias = normalize_name(resolved_rel.alias, case_sensitive=case_sensitive)
                        rel_table = normalize_name(resolved_rel.table, case_sensitive=case_sensitive)
                        if src_table != rel_alias and src_table != rel_table:
                            continue
                    for col_dict in resolved_rel.columns:
                        if normalize_name(col_dict["column_name"], case_sensitive=case_sensitive) == src_col_name:
                            return ResolvedColumnRef(
                                reference=cte_match.reference,
                                relation_id=resolved_rel.relation_id,
                                column_entity_id=EntityIdFactory.column(
                                    resolved_rel.catalog,
                                    resolved_rel.schema,
                                    resolved_rel.table,
                                    col_dict["column_name"],
                                ),
                                table_entity_id=resolved_rel.table_entity_id,
                                catalog=resolved_rel.catalog,
                                schema=resolved_rel.schema,
                                table=resolved_rel.table,
                                column=col_dict["column_name"],
                                data_type=col_dict.get("data_type"),
                                comment=col_dict.get("comment"),
                            )
                # ── 降级：无元数据时，从 scope_model.relations 匹配表 ──
                for relation in scope_model.relations:
                    # 检查源列所属的表是否匹配当前 relation
                    if src_col.table:
                        src_table = normalize_name(src_col.table, case_sensitive=case_sensitive)
                        rel_alias = normalize_name(relation.alias, case_sensitive=case_sensitive)
                        rel_table = normalize_name(relation.table, case_sensitive=case_sensitive)
                        if src_table != rel_alias and src_table != rel_table:
                            continue
                    # 源列来自 CTE：递归穿透到更底层
                    if relation.is_cte:
                        next_cte_name = relation.table.lower()
                        next_cols = scope_model.cte_columns.get(next_cte_name, [])
                        for ncol in next_cols:
                            if normalize_name(ncol.output_name, case_sensitive=case_sensitive) == src_col_name:
                                # 构造虚拟的 ResolvedColumnRef 代表该 CTE 列，再递归
                                virtual_match = ResolvedColumnRef(
                                    reference=cte_match.reference,
                                    relation_id=relation.relation_id,
                                    column_entity_id=EntityIdFactory.column(
                                        relation.catalog, relation.schema, relation.table, ncol.output_name,
                                    ),
                                    table_entity_id=relation.table_entity_id,
                                    catalog=relation.catalog,
                                    schema=relation.schema,
                                    table=relation.table,
                                    column=ncol.output_name,
                                )
                                deeper = self._trace_cte_column_from_match(
                                    virtual_match, scope_model, resolved_relations, case_sensitive, _depth + 1,
                                )
                                if deeper:
                                    return deeper
                        continue
                    # 找到了物理表，即使没有元数据也创建引用
                    return ResolvedColumnRef(
                        reference=cte_match.reference,
                        relation_id=relation.relation_id,
                        column_entity_id=EntityIdFactory.column(
                            relation.catalog,
                            relation.schema,
                            relation.table,
                            src_col.column,
                        ),
                        table_entity_id=relation.table_entity_id,
                        catalog=relation.catalog,
                        schema=relation.schema,
                        table=relation.table,
                        column=src_col.column,
                        data_type=None,
                        comment=None,
                    )
        return None

    # ── M19: Join 消歧 ──
    @staticmethod
    def _join_disambiguate(
        reference: ColumnReference,
        matches: list[ResolvedColumnRef],
        scope_model: ScopeModel,
        *,
        case_sensitive: bool,
    ) -> ResolvedColumnRef | None:
        """If a column is ambiguous but all candidate tables are equi-joined on this
        column (per ON clause), the column is semantically equivalent across tables.
        We resolve to the first matching relation."""
        if not scope_model.join_keys or len(matches) <= 1:
            return None

        col_name = normalize_name(reference.column, case_sensitive=case_sensitive)
        # Collect table aliases from matches
        match_aliases: set[str] = {
            normalize_name(m.alias, case_sensitive=case_sensitive)
            if hasattr(m, "alias") else ""
            for m in matches
        }

        # Build a graph of tables connected by equi-joins on this column
        connected: set[str] = set()
        for key in scope_model.join_keys:
            left_col = normalize_name(key.left.column, case_sensitive=case_sensitive)
            right_col = normalize_name(key.right.column, case_sensitive=case_sensitive)
            if left_col == col_name and right_col == col_name:
                left_table = normalize_name(key.left.table or "", case_sensitive=case_sensitive)
                right_table = normalize_name(key.right.table or "", case_sensitive=case_sensitive)
                if left_table in match_aliases or right_table in match_aliases:
                    connected.add(left_table)
                    connected.add(right_table)

        # If all match aliases are in the connected set, they are equi-joined
        if match_aliases and match_aliases.issubset(connected):
            return matches[0]

        return None

    # ── M19: CTE 字段回溯 ──
    @staticmethod
    def _get_cte_columns_for_relation(
        relation: ScopeRelation,
        scope_model: ScopeModel,
    ) -> list[dict]:
        """Convert CteInternalColumn entries to column dicts for ResolvedRelation."""
        cte_name = relation.table.lower()
        internal_columns = scope_model.cte_columns.get(cte_name, [])
        return [
            {
                "column_name": col.output_name,
                "normalized_column_name": col.output_name.lower(),
                "data_type": "unknown",
                "comment": f"CTE 输出列 (来源: {cte_name})",
                "ordinal": col.ordinal,
            }
            for col in internal_columns
        ]

    def _trace_cte_column(
        self,
        reference: ColumnReference,
        scope_model: ScopeModel,
        resolved_relations: list[ResolvedRelation],
        *,
        case_sensitive: bool,
    ) -> ResolvedColumnRef | None:
        """Trace a CTE column reference back through the CTE body to the
        underlying physical table column.

        Returns a ResolvedColumnRef pointing to the deepest source, or None
        if the trace cannot be completed."""
        cte_relation = self._find_cte_relation(reference, scope_model.relations, case_sensitive)
        if cte_relation is None:
            return None

        cte_name = cte_relation.table.lower()
        internal_columns = scope_model.cte_columns.get(cte_name, [])
        col_name = normalize_name(reference.column, case_sensitive=case_sensitive)

        # Find matching CTE internal column by output name
        matching_icol: CteInternalColumn | None = None
        for icol in internal_columns:
            if normalize_name(icol.output_name, case_sensitive=case_sensitive) == col_name:
                matching_icol = icol
                break

        if matching_icol is None:
            return None

        # If the CTE internal column has source columns, try to resolve to a physical table
        if matching_icol.source_columns:
            for src_col in matching_icol.source_columns:
                # Try to resolve against physical table columns
                for resolved_rel in resolved_relations:
                    if resolved_rel.is_cte:
                        continue
                    if src_col.table and normalize_name(src_col.table, case_sensitive=case_sensitive) != \
                       normalize_name(resolved_rel.alias, case_sensitive=case_sensitive):
                        continue
                    for col_dict in resolved_rel.columns:
                        if normalize_name(col_dict["column_name"], case_sensitive=case_sensitive) == \
                           normalize_name(src_col.column, case_sensitive=case_sensitive):
                            return ResolvedColumnRef(
                                reference=reference,
                                relation_id=resolved_rel.relation_id,
                                column_entity_id=EntityIdFactory.column(
                                    resolved_rel.catalog,
                                    resolved_rel.schema,
                                    resolved_rel.table,
                                    col_dict["column_name"],
                                ),
                                table_entity_id=resolved_rel.table_entity_id,
                                catalog=resolved_rel.catalog,
                                schema=resolved_rel.schema,
                                table=resolved_rel.table,
                                column=col_dict["column_name"],
                                data_type=col_dict.get("data_type"),
                                comment=col_dict.get("comment"),
                            )

        # ── 递归穿透：source_columns 可能来自其他 CTE，继续向下追溯 ──
        for src_col in matching_icol.source_columns:
            for relation in scope_model.relations:
                # 匹配表：有 table 限定符时精确匹配，无 table 时匹配任意非 CTE 表
                if src_col.table:
                    src_table = normalize_name(src_col.table, case_sensitive=case_sensitive)
                    rel_alias = normalize_name(relation.alias, case_sensitive=case_sensitive)
                    rel_table = normalize_name(relation.table, case_sensitive=case_sensitive)
                    if src_table != rel_alias and src_table != rel_table:
                        continue
                elif relation.is_cte:
                    continue  # 无 table 限定符时跳过 CTE，优先匹配物理表
                if relation.is_cte:
                    # 源列来自另一个 CTE → 递归穿透
                    next_cte_name = relation.table.lower()
                    next_cols = scope_model.cte_columns.get(next_cte_name, [])
                    src_col_name = normalize_name(src_col.column, case_sensitive=case_sensitive)
                    for ncol in next_cols:
                        if normalize_name(ncol.output_name, case_sensitive=case_sensitive) == src_col_name:
                            virtual_match = ResolvedColumnRef(
                                reference=reference, relation_id=relation.relation_id,
                                column_entity_id=EntityIdFactory.column(
                                    relation.catalog, relation.schema, relation.table, ncol.output_name,
                                ),
                                table_entity_id=relation.table_entity_id,
                                catalog=relation.catalog, schema=relation.schema,
                                table=relation.table, column=ncol.output_name,
                            )
                            deeper = self._trace_cte_column_from_match(
                                virtual_match, scope_model, resolved_relations, case_sensitive, _depth + 1,
                            )
                            if deeper:
                                return deeper
                    continue
                # 找到物理表 → 创建引用
                return ResolvedColumnRef(
                    reference=reference, relation_id=relation.relation_id,
                    column_entity_id=EntityIdFactory.column(
                        relation.catalog, relation.schema, relation.table, src_col.column,
                    ),
                    table_entity_id=relation.table_entity_id,
                    catalog=relation.catalog, schema=relation.schema,
                    table=relation.table, column=src_col.column,
                )

        # Fallback: create a CTE-sourced ResolvedColumnRef
        return ResolvedColumnRef(
            reference=reference,
            relation_id=cte_relation.relation_id,
            column_entity_id=EntityIdFactory.column(
                "cte", cte_name, cte_name, reference.column,
            ),
            table_entity_id=cte_relation.table_entity_id,
            catalog="cte",
            schema=cte_name,
            table=cte_name,
            column=reference.column,
            data_type="unknown",
            comment=f"CTE {cte_name} 输出列",
        )

    @staticmethod
    def _find_cte_relation(
        reference: ColumnReference,
        scope_relations: list[ScopeRelation],
        case_sensitive: bool,
    ) -> ScopeRelation | None:
        """Find the CTE relation that a column reference points to."""
        if not reference.table:
            return None
        table_ref = normalize_name(reference.table, case_sensitive=case_sensitive)
        for relation in scope_relations:
            if not relation.is_cte:
                continue
            if normalize_name(relation.alias, case_sensitive=case_sensitive) == table_ref:
                return relation
            if normalize_name(relation.table, case_sensitive=case_sensitive) == table_ref:
                return relation
        return None

    def _resolve_reference(
        self,
        reference: ColumnReference,
        scope_relations: list[ScopeRelation],
        resolved_relations: list[ResolvedRelation],
        *,
        case_sensitive: bool,
    ) -> list[ResolvedColumnRef]:
        relation_candidates = resolved_relations
        if reference.table:
            alias = normalize_name(reference.table, case_sensitive=case_sensitive)
            valid_aliases = {
                normalize_name(r.alias, case_sensitive=case_sensitive): r.relation_id
                for r in scope_relations
            }
            relation_id = valid_aliases.get(alias)
            if relation_id is None:
                relation_id = next(
                    (
                        r.relation_id
                        for r in scope_relations
                        if normalize_name(r.table, case_sensitive=case_sensitive) == alias
                    ),
                    None,
                )
            relation_candidates = [
                r for r in resolved_relations if r.relation_id == relation_id
            ]

        column_name = normalize_name(reference.column, case_sensitive=case_sensitive)
        matches: list[ResolvedColumnRef] = []
        for relation in relation_candidates:
            for column in relation.columns:
                candidate = normalize_name(
                    column["column_name"],
                    case_sensitive=case_sensitive,
                )
                if candidate != column_name:
                    continue
                matches.append(
                    ResolvedColumnRef(
                        reference=reference,
                        relation_id=relation.relation_id,
                        column_entity_id=EntityIdFactory.column(
                            relation.catalog,
                            relation.schema,
                            relation.table,
                            column["column_name"],
                        ),
                        table_entity_id=relation.table_entity_id,
                        catalog=relation.catalog,
                        schema=relation.schema,
                        table=relation.table,
                        column=column["column_name"],
                        data_type=column.get("data_type"),
                        comment=column.get("comment"),
                    )
                )
        return matches

    @staticmethod
    def _references_missing_relation(
        reference: ColumnReference,
        scope_relations: list[ScopeRelation],
        missing_relation_ids: set[str],
        *,
        case_sensitive: bool,
    ) -> bool:
        if not reference.table:
            return False
        table_ref = normalize_name(reference.table, case_sensitive=case_sensitive)
        for relation in scope_relations:
            if relation.relation_id not in missing_relation_ids:
                continue
            if normalize_name(relation.alias, case_sensitive=case_sensitive) == table_ref:
                return True
            if normalize_name(relation.table, case_sensitive=case_sensitive) == table_ref:
                return True
        return False

    @staticmethod
    def _references_cte_relation(
        reference: ColumnReference,
        scope_relations: list[ScopeRelation],
        *,
        case_sensitive: bool,
    ) -> bool:
        """检查列引用是否指向一个 CTE 表（WITH 子句中定义的临时表）。"""
        if not reference.table:
            return False
        table_ref = normalize_name(reference.table, case_sensitive=case_sensitive)
        for relation in scope_relations:
            if not relation.is_cte:
                continue
            if normalize_name(relation.alias, case_sensitive=case_sensitive) == table_ref:
                return True
            if normalize_name(relation.table, case_sensitive=case_sensitive) == table_ref:
                return True
        return False

    # ── M19: UNION 多来源字段合并 ──
    def _resolve_union_columns(
        self,
        scope_model: ScopeModel,
        resolved_relations: list[ResolvedRelation],
        *,
        case_sensitive: bool,
    ) -> tuple[list[ResolvedColumnRef], list[UnresolvedColumnRef]]:
        """For UNION queries, resolve columns from each segment and mark
        output columns as union_mapping."""
        resolved: list[ResolvedColumnRef] = []
        unresolved: list[UnresolvedColumnRef] = []

        # Build a resolved relation lookup from the main scope
        relation_by_alias: dict[str, ResolvedRelation] = {}
        for rr in resolved_relations:
            alias = normalize_name(rr.alias, case_sensitive=case_sensitive)
            relation_by_alias[alias] = rr
            tbl = normalize_name(rr.table, case_sensitive=case_sensitive)
            relation_by_alias[tbl] = rr

        # For each union segment, resolve its select item sources
        for segment in scope_model.union_segments:
            for item in segment.select_items:
                for reference in item.source_columns:
                    col_name = normalize_name(reference.column, case_sensitive=case_sensitive)
                    matched = False
                    for relation in segment.relations:
                        alias = normalize_name(relation.alias, case_sensitive=case_sensitive)
                        rr = relation_by_alias.get(alias)
                        if rr is None:
                            tbl_name = normalize_name(relation.table, case_sensitive=case_sensitive)
                            rr = relation_by_alias.get(tbl_name)
                        if rr is None:
                            continue
                        for col_dict in rr.columns:
                            if normalize_name(col_dict["column_name"], case_sensitive=case_sensitive) == col_name:
                                resolved.append(
                                    ResolvedColumnRef(
                                        reference=reference,
                                        relation_id=rr.relation_id,
                                        column_entity_id=EntityIdFactory.column(
                                            rr.catalog, rr.schema, rr.table, col_dict["column_name"],
                                        ),
                                        table_entity_id=rr.table_entity_id,
                                        catalog=rr.catalog,
                                        schema=rr.schema,
                                        table=rr.table,
                                        column=col_dict["column_name"],
                                        data_type=col_dict.get("data_type"),
                                        comment=col_dict.get("comment"),
                                    )
                                )
                                matched = True
                                break
                        if matched:
                            break

        return resolved, unresolved
