"""P0 NameResolver: resolve scope columns against imported metadata."""

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
from app.domain.scope_model import ColumnReference, ScopeModel, ScopeRelation
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
                    DiagnosticLevel.error,
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
                matches = self._resolve_reference(
                    reference,
                    scope_model.relations,
                    resolved_relations,
                    case_sensitive=case_sensitive,
                )
                if len(matches) == 1:
                    resolved_columns.append(matches[0])
                    continue

                if len(matches) > 1:
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
