"""Internal models for table and column name resolution."""

from __future__ import annotations

from pydantic import Field

from app.domain.contracts import MetadataContext, StrictBaseModel
from app.domain.scope_model import ColumnReference


class ResolvedRelation(StrictBaseModel):
    relation_id: str
    alias: str
    catalog: str
    schema: str
    table: str
    table_entity_id: str
    table_row: dict
    columns: list[dict] = Field(default_factory=list)
    is_cte: bool = False


class ResolvedColumnRef(StrictBaseModel):
    reference: ColumnReference
    relation_id: str
    column_entity_id: str
    table_entity_id: str
    catalog: str
    schema: str
    table: str
    column: str
    data_type: str | None = None
    comment: str | None = None


class UnresolvedColumnRef(StrictBaseModel):
    reference: ColumnReference
    reason: str
    candidate_columns: list[str] = Field(default_factory=list)


class NameResolutionResult(StrictBaseModel):
    metadata_context: MetadataContext
    resolved_relations: list[ResolvedRelation] = Field(default_factory=list)
    resolved_columns: list[ResolvedColumnRef] = Field(default_factory=list)
    unresolved_columns: list[UnresolvedColumnRef] = Field(default_factory=list)
