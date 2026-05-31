"""Minimal SELECT projection extractor for P0 lineage."""

from __future__ import annotations

from app.domain.entity_id import EntityIdFactory
from app.domain.minimal_expression_model import (
    ProjectionItem,
    ProjectionModel,
    ProjectionSourceRef,
)
from app.domain.name_resolution_model import NameResolutionResult
from app.domain.scope_model import ColumnReference, ScopeModel


class ProjectionExtractor:
    def extract(
        self,
        scope_model: ScopeModel,
        name_resolution: NameResolutionResult,
    ) -> ProjectionModel:
        resolved_by_ref = self._resolved_lookup(name_resolution)
        unresolved_by_ref = self._unresolved_lookup(name_resolution)
        projections: list[ProjectionItem] = []
        unsupported: list[str] = []

        for item in scope_model.select_items:
            output_entity_id = EntityIdFactory.output_column(
                item.scope_id,
                item.output_name,
                item.ordinal,
            )
            source_refs: list[ProjectionSourceRef] = []
            for reference in item.source_columns:
                key = self._ref_key(reference)
                resolved = resolved_by_ref.get(key)
                unresolved_reason = unresolved_by_ref.get(key)
                source_refs.append(
                    ProjectionSourceRef(
                        raw=reference.raw,
                        column_entity_id=resolved,
                        unresolved_reason=unresolved_reason,
                    )
                )

            literal_value = None
            if item.expression_kind == "literal":
                literal_value = item.expression_sql
            unsupported_reason = None
            if item.expression_kind == "expression" and not source_refs and not literal_value:
                unsupported_reason = "expression_without_direct_source"
                unsupported.append(f"{item.output_name}: {item.expression_sql}")

            projections.append(
                ProjectionItem(
                    projection_id=f"projection:{item.scope_id}:{item.ordinal}",
                    scope_id=item.scope_id,
                    ordinal=item.ordinal,
                    output_name=item.output_name,
                    output_entity_id=output_entity_id,
                    expression_sql=item.expression_sql,
                    expression_kind=item.expression_kind,
                    source_refs=source_refs,
                    literal_value=literal_value,
                    unsupported_reason=unsupported_reason,
                )
            )

        return ProjectionModel(
            projections=projections,
            unsupported_expressions=unsupported,
        )

    @staticmethod
    def _ref_key(reference: ColumnReference) -> tuple[str | None, str]:
        return (reference.table.lower() if reference.table else None, reference.column.lower())

    def _resolved_lookup(self, name_resolution: NameResolutionResult) -> dict[tuple[str | None, str], str]:
        lookup: dict[tuple[str | None, str], str] = {}
        for resolved in name_resolution.resolved_columns:
            key = self._ref_key(resolved.reference)
            lookup.setdefault(key, resolved.column_entity_id)
        return lookup

    def _unresolved_lookup(self, name_resolution: NameResolutionResult) -> dict[tuple[str | None, str], str]:
        lookup: dict[tuple[str | None, str], str] = {}
        for unresolved in name_resolution.unresolved_columns:
            key = self._ref_key(unresolved.reference)
            lookup.setdefault(key, unresolved.reason)
        return lookup
