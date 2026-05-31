"""Projection model consumed by the P0 lineage engine."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.contracts import StrictBaseModel


class ProjectionSourceRef(StrictBaseModel):
    raw: str
    column_entity_id: str | None = None
    relation_id: str | None = None
    unresolved_reason: str | None = None


class ProjectionItem(StrictBaseModel):
    projection_id: str
    scope_id: str
    ordinal: int
    output_name: str
    output_entity_id: str
    expression_sql: str
    expression_kind: Literal["column", "literal", "function", "expression"]
    source_refs: list[ProjectionSourceRef] = Field(default_factory=list)
    literal_value: str | None = None
    unsupported_reason: str | None = None


class ProjectionModel(StrictBaseModel):
    projections: list[ProjectionItem] = Field(default_factory=list)
    unsupported_expressions: list[str] = Field(default_factory=list)
