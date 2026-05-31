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
    is_cte: bool = False


class ScopeSelectItem(StrictBaseModel):
    select_id: str
    scope_id: str
    ordinal: int
    expression_sql: str
    output_name: str
    alias: str | None = None
    expression_kind: Literal["column", "literal", "function", "expression"] = "expression"
    source_columns: list[ColumnReference] = Field(default_factory=list)


class JoinKey(StrictBaseModel):
    """Represents a pair of columns equated in a JOIN ON clause."""
    left: ColumnReference
    right: ColumnReference
    raw_sql: str = ""


class CteInternalColumn(StrictBaseModel):
    """Describes a CTE output column and its source in the CTE body."""
    cte_name: str
    output_name: str
    ordinal: int
    expression_sql: str
    source_columns: list[ColumnReference] = Field(default_factory=list)
    expression_kind: str = "expression"


class UnionSegment(StrictBaseModel):
    """A single segment within a UNION / UNION ALL query."""
    segment_index: int
    alias: str = ""
    relations: list[ScopeRelation] = Field(default_factory=list)
    select_items: list[ScopeSelectItem] = Field(default_factory=list)
    raw_sql: str = ""


class ScopeModel(StrictBaseModel):
    scope_id: str = "scope:root"
    scope_type: Literal["root", "cte", "subquery"] = "root"
    relations: list[ScopeRelation] = Field(default_factory=list)
    select_items: list[ScopeSelectItem] = Field(default_factory=list)
    # M19 enhancements
    join_keys: list[JoinKey] = Field(default_factory=list)
    cte_columns: dict[str, list[CteInternalColumn]] = Field(default_factory=dict)
    cte_source_names: dict[str, list[str]] = Field(default_factory=dict)
    union_segments: list[UnionSegment] = Field(default_factory=list)
    parent_scope_id: str | None = None
