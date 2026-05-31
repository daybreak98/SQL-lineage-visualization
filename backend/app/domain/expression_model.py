"""M23 (R13a) ExpressionModel: aggregate / CASE WHEN / window function analysis results."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.contracts import StrictBaseModel
from app.domain.scope_model import ColumnReference


class AggregateExpression(StrictBaseModel):
    """An aggregate function (SUM / COUNT / AVG / MAX / MIN / COUNT_DISTINCT)."""

    expression_id: str
    scope_id: str
    ordinal: int
    function_name: str  # "SUM", "COUNT", "AVG", "MAX", "MIN", "COUNT_DISTINCT", ...
    expression_sql: str
    source_columns: list[ColumnReference] = Field(default_factory=list)
    is_distinct: bool = False
    args_sql: str | None = None


class CaseBranch(StrictBaseModel):
    """Single WHEN … THEN branch inside a CASE expression."""

    condition_sql: str
    value_sql: str
    source_columns: list[ColumnReference] = Field(default_factory=list)


class CaseWhenExpression(StrictBaseModel):
    """A CASE WHEN expression with its branches and default value."""

    expression_id: str
    scope_id: str
    ordinal: int
    expression_sql: str
    branches: list[CaseBranch] = Field(default_factory=list)
    default_value_sql: str | None = None
    source_columns: list[ColumnReference] = Field(default_factory=list)


class WindowFunction(StrictBaseModel):
    """A window function (ROW_NUMBER / RANK / DENSE_RANK / LEAD / LAG / etc.)
    including its PARTITION BY and ORDER BY source columns."""

    expression_id: str
    scope_id: str
    ordinal: int
    function_name: str  # "ROW_NUMBER", "RANK", "SUM", etc. (inner function)
    expression_sql: str
    partition_by_columns: list[ColumnReference] = Field(default_factory=list)
    order_by_columns: list[ColumnReference] = Field(default_factory=list)
    source_columns: list[ColumnReference] = Field(default_factory=list)


class ExpressionModel(StrictBaseModel):
    """Aggregate model of expressions found in a query's SELECT clause."""

    aggregates: list[AggregateExpression] = Field(default_factory=list)
    case_whens: list[CaseWhenExpression] = Field(default_factory=list)
    window_functions: list[WindowFunction] = Field(default_factory=list)
    unsupported: list[str] = Field(default_factory=list)
