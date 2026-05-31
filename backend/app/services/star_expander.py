"""StarExpander: expand SELECT * and alias.* into concrete column lists using metadata.

Part of M20 (R11a) - select * metadata-driven expansion.
Runs between NameResolver and ProjectionExtractor, consuming name_resolution's
resolved_relations to produce expanded ScopeSelectItems and corresponding
ResolvedColumnRef entries.
"""

from __future__ import annotations

from app.diagnostics.collector import DiagnosticsCollector
from app.domain.contracts import Diagnostic, DiagnosticCode, DiagnosticLevel
from app.domain.entity_id import EntityIdFactory, normalize_name
from app.domain.name_resolution_model import (
    NameResolutionResult,
    ResolvedColumnRef,
    ResolvedRelation,
)
from app.domain.scope_model import ColumnReference, ScopeModel, ScopeRelation, ScopeSelectItem
from app.services.metadata_service import MetadataService


class StarExpander:
    """Expand SELECT * and alias.* into explicit column references.

    Consumes name_resolution.resolved_relations (which already contain metadata columns)
    to produce expanded ScopeSelectItems with concrete source_columns, and
    corresponding ResolvedColumnRef entries for the projection pipeline.
    """

    def __init__(self, metadata_service: MetadataService):
        self.metadata_service = metadata_service

    def expand(
        self,
        scope_model: ScopeModel,
        name_resolution: NameResolutionResult,
        metadata_version: str,
    ) -> tuple[list[ScopeSelectItem], list[ResolvedColumnRef], list[Diagnostic]]:
        """Expand star patterns in select items.

        Returns:
            expanded_items: list of ScopeSelectItem with `*` replaced by concrete columns
            extra_resolved_columns: ResolvedColumnRef entries for expanded columns
            diagnostics: STAR_EXPANSION_FAILED diagnostics when metadata is missing
        """
        collector = DiagnosticsCollector()
        expanded_items: list[ScopeSelectItem] = []
        extra_resolved: list[ResolvedColumnRef] = []

        # ── Build alias → ResolvedRelation lookup ──
        relation_by_alias: dict[str, ResolvedRelation] = {}
        for rr in name_resolution.resolved_relations:
            relation_by_alias[normalize_name(rr.alias)] = rr
            relation_by_alias[normalize_name(rr.table)] = rr

        # ── Build alias → ScopeRelation lookup for is_cte check ──
        scope_relation_by_alias: dict[str, ScopeRelation] = {}
        for sr in scope_model.relations:
            scope_relation_by_alias[normalize_name(sr.alias)] = sr
            scope_relation_by_alias[normalize_name(sr.table)] = sr

        # ── Collect physical (non-CTE) relations for unqualified `*` expansion ──
        physical_relations: list[ResolvedRelation] = [
            rr for rr in name_resolution.resolved_relations
            if not rr.is_cte
        ]

        ordinal_counter = 1
        scope_id = scope_model.scope_id

        for item in scope_model.select_items:
            sql = item.expression_sql.strip()

            star_match = self._detect_star(sql)
            if star_match is None:
                # ── Not a star: pass through with renumbered ordinal ──
                expanded_items.append(
                    item.model_copy(update={"ordinal": ordinal_counter})
                )
                ordinal_counter += 1
                continue

            if star_match == "*":
                # ── Unqualified `*`: expand all physical tables ──
                if not physical_relations:
                    collector.add(
                        DiagnosticCode.STAR_EXPANSION_FAILED,
                        DiagnosticLevel.warning,
                        "SELECT * 展开失败: 当前 scope 没有可用的物理表",
                        suggestion="请检查 FROM 子句是否引用了有效的表",
                        related_entity_ids=[scope_id],
                        details={"expression_sql": sql},
                    )
                    # Keep the original star item as fallback
                    expanded_items.append(
                        item.model_copy(update={"ordinal": ordinal_counter})
                    )
                    ordinal_counter += 1
                    continue

                for relation in physical_relations:
                    if not relation.columns:
                        collector.add(
                            DiagnosticCode.STAR_EXPANSION_FAILED,
                            DiagnosticLevel.warning,
                            f"SELECT * 展开失败: 表 {relation.table} 在元数据中没有字段信息",
                            suggestion="请确认该表的元数据已正确导入",
                            related_entity_ids=[relation.table_entity_id],
                            details={
                                "table": relation.table,
                                "alias": relation.alias,
                            },
                        )
                        continue

                    for col_dict in sorted(relation.columns, key=lambda c: c.get("ordinal", 0) or 0):
                        col_name = col_dict["column_name"]
                        expanded_item, resolved_ref = self._build_expanded_item(
                            scope_id=scope_id,
                            ordinal=ordinal_counter,
                            relation=relation,
                            col_dict=col_dict,
                            alias=relation.alias,
                        )
                        expanded_items.append(expanded_item)
                        extra_resolved.append(resolved_ref)
                        ordinal_counter += 1

            else:
                # ── Qualified `alias.*`: expand specific table ──
                alias = star_match  # e.g., "o" from "o.*"
                rr = relation_by_alias.get(normalize_name(alias))
                if rr is None:
                    collector.add(
                        DiagnosticCode.STAR_EXPANSION_FAILED,
                        DiagnosticLevel.warning,
                        f"{alias}.* 展开失败: 找不到别名 '{alias}' 对应的表",
                        suggestion="请检查表别名是否正确",
                        related_entity_ids=[scope_id],
                        details={"alias": alias, "expression_sql": sql},
                    )
                    expanded_items.append(
                        item.model_copy(update={"ordinal": ordinal_counter})
                    )
                    ordinal_counter += 1
                    continue

                if not rr.columns:
                    collector.add(
                        DiagnosticCode.STAR_EXPANSION_FAILED,
                        DiagnosticLevel.warning,
                        f"{alias}.* 展开失败: 表 {rr.table} 在元数据中没有字段信息",
                        suggestion="请确认该表的元数据已正确导入",
                        related_entity_ids=[rr.table_entity_id],
                        details={"table": rr.table, "alias": alias},
                    )
                    expanded_items.append(
                        item.model_copy(update={"ordinal": ordinal_counter})
                    )
                    ordinal_counter += 1
                    continue

                for col_dict in sorted(rr.columns, key=lambda c: c.get("ordinal", 0) or 0):
                    col_name = col_dict["column_name"]
                    expanded_item, resolved_ref = self._build_expanded_item(
                        scope_id=scope_id,
                        ordinal=ordinal_counter,
                        relation=rr,
                        col_dict=col_dict,
                        alias=alias,
                    )
                    expanded_items.append(expanded_item)
                    extra_resolved.append(resolved_ref)
                    ordinal_counter += 1

        return expanded_items, extra_resolved, collector.list()

    # ── helpers ──

    @staticmethod
    def _detect_star(expression_sql: str) -> str | None:
        """Detect star pattern in expression SQL.

        Returns:
            "*" for unqualified star (SELECT *)
            "alias" for qualified star (SELECT alias.*)
            None if not a star pattern
        """
        sql = expression_sql.strip()
        if sql == "*":
            return "*"
        if sql.endswith(".*") and len(sql) > 2:
            alias_part = sql[:-2].strip()
            if alias_part and not any(c in alias_part for c in (" ", "(", ")", ",")):
                # Valid alias: no spaces, no parens, no commas
                return alias_part
        return None

    @staticmethod
    def _build_expanded_item(
        scope_id: str,
        ordinal: int,
        relation: ResolvedRelation,
        col_dict: dict,
        alias: str,
    ) -> tuple[ScopeSelectItem, ResolvedColumnRef]:
        """Build a ScopeSelectItem and ResolvedColumnRef for a single expanded column."""
        col_name = col_dict["column_name"]
        data_type = col_dict.get("data_type", "unknown")
        comment = col_dict.get("comment")

        # Build the qualified reference used in expression SQL
        expression_sql = f"{alias}.{col_name}"

        column_ref = ColumnReference(
            raw=expression_sql,
            column=col_name,
            table=alias,
        )

        column_entity_id = EntityIdFactory.column(
            relation.catalog,
            relation.schema,
            relation.table,
            col_name,
        )

        select_item = ScopeSelectItem(
            select_id=f"select:{scope_id}:star:{ordinal}",
            scope_id=scope_id,
            ordinal=ordinal,
            expression_sql=expression_sql,
            output_name=col_name,
            alias=col_name,
            expression_kind="column",
            source_columns=[column_ref],
        )

        resolved_ref = ResolvedColumnRef(
            reference=column_ref,
            relation_id=relation.relation_id,
            column_entity_id=column_entity_id,
            table_entity_id=relation.table_entity_id,
            catalog=relation.catalog,
            schema=relation.schema,
            table=relation.table,
            column=col_name,
            data_type=data_type,
            comment=comment,
        )

        return select_item, resolved_ref
