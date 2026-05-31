"""P2 SemanticsReport typed models for evidence-driven query caliber analysis.

Each model carries `evidence_refs` that point at entity_id / location_id anchors
in the lineage IR or source locations, making every deterministic conclusion traceable.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.domain.contracts import StrictBaseModel


class ResultGrain(StrictBaseModel):
    """Describes the grain (result row uniqueness) of the query output."""

    grain_type: Literal[
        "group_by",          # GROUP BY 聚合粒度
        "distinct",          # SELECT DISTINCT
        "detail",            # 明细行（无 GROUP BY / DISTINCT）
        "window_partition",  # 窗口函数 PARTITION BY
        "unknown",
    ]
    columns: list[str] = Field(
        default_factory=list,
        description="Columns defining the grain (GROUP BY cols / DISTINCT cols)",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Entity IDs or location IDs that serve as evidence",
    )


class FilterInfo(StrictBaseModel):
    """Single filtering / scoping condition extracted from the query."""

    filter_type: Literal[
        "where",             # WHERE clause
        "having",            # HAVING clause
        "partition_filter",  # 分区裁剪条件 (e.g., dt = 'xxx')
        "join_condition",    # JOIN ON 条件（也用于过滤）
        "subquery_filter",   # 子查询中的过滤条件
    ]
    expression: str = Field(description="The filter expression SQL text")
    involved_columns: list[str] = Field(
        default_factory=list,
        description="Column entity IDs involved in the filter",
    )
    evidence_refs: list[str] = Field(default_factory=list)


class MetricInfo(StrictBaseModel):
    """An aggregation metric formula."""

    metric_type: Literal[
        "sum",
        "count",
        "avg",
        "min",
        "max",
        "count_distinct",
        "custom_aggregate",
        "expression",
    ]
    expression: str = Field(description="The metric expression SQL (e.g., SUM(salary))")
    output_name: str = ""
    target_column: str | None = Field(
        default=None,
        description="Entity ID of the underlying column (when traceable)",
    )
    evidence_refs: list[str] = Field(default_factory=list)


class JoinInfo(StrictBaseModel):
    """A JOIN relationship with type, keys, and amplification risk assessment."""

    join_type: str = Field(description="inner | left | right | cross | implicit")
    left_table: str = Field(description="Left table entity ID or label")
    right_table: str = Field(description="Right table entity ID or label")
    join_keys: list[str] = Field(
        default_factory=list,
        description="Join key expressions (e.g., a.user_id = b.user_id)",
    )
    amplification_risk: Literal["none", "low", "medium", "high"] = "none"
    risk_reason: str = ""
    evidence_refs: list[str] = Field(default_factory=list)


class DedupRule(StrictBaseModel):
    """A deduplication / uniqueness rule applied in the query."""

    dedup_type: Literal[
        "distinct",         # SELECT DISTINCT
        "row_number",       # ROW_NUMBER() OVER (...) = 1
        "group_by",         # GROUP BY (implicit dedup)
        "union",            # UNION (vs UNION ALL)
        "qualify",          # QUALIFY clause
    ]
    description: str
    evidence_refs: list[str] = Field(default_factory=list)


class RiskInfo(StrictBaseModel):
    """A semantic risk or anti-pattern detected in the query."""

    risk_type: Literal[
        "join_amplification",    # JOIN 可能放大行数
        "grain_mixing",          # 多粒度混杂（明细 + 聚合）
        "no_partition_filter",   # 无分区过滤（大表全扫描）
        "potential_cartesian",   # 潜在笛卡尔积（无 ON 子句的 JOIN）
        "ambiguous_metrics",     # 指标表达式有歧义
    ]
    severity: Literal["info", "warning", "error"]
    description: str
    evidence_refs: list[str] = Field(default_factory=list)


class SemanticsAnalysisResult(StrictBaseModel):
    """Internal typed semantics analysis result.

    This is produced by SemanticsAnalyzer and then projected into the public
    contracts.SemanticsReport for the API response.
    """

    status: Literal["success", "partial"] = "success"
    result_grain: ResultGrain | None = None
    filters: list[FilterInfo] = Field(default_factory=list)
    metrics: list[MetricInfo] = Field(default_factory=list)
    joins: list[JoinInfo] = Field(default_factory=list)
    dedup_logic: list[DedupRule] = Field(default_factory=list)
    semantic_risks: list[RiskInfo] = Field(default_factory=list)
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Aggregated list of all evidence references",
    )
