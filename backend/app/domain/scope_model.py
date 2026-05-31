"""Internal scope model produced by ScopeResolver."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.contracts import StrictBaseModel


class ColumnReference(StrictBaseModel):
    raw: str
    column: str
    table: str | None = None
    schema: str | None = None
    catalog: str | None = None


class ScopeRelation(StrictBaseModel):
    relation_id: str
    scope_id: str
    alias: str
    catalog: str
    schema: str
    table: str
    table_entity_id: str
    source_name: str


class ScopeSelectItem(StrictBaseModel):
    select_id: str
    scope_id: str
    ordinal: int
    expression_sql: str
    output_name: str
    alias: str | None = None
    expression_kind: Literal["column", "literal", "function", "expression"] = "expression"
    source_columns: list[ColumnReference] = Field(default_factory=list)


class ScopeModel(StrictBaseModel):
    scope_id: str = "scope:root"
    scope_type: Literal["root", "cte", "subquery"] = "root"
    relations: list[ScopeRelation] = Field(default_factory=list)
    select_items: list[ScopeSelectItem] = Field(default_factory=list)
