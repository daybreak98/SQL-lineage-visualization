"""P2 SemanticsAnalyzer — evidence-driven query caliber analysis.

Takes the expression model, lineage IR, metadata context, scope model, and parse result
to produce a SemanticsAnalysisResult with traceable evidence references.
"""

from __future__ import annotations

from sqlglot import exp

from app.domain.contracts import LineageIR, MetadataContext, SourceLocation
from app.domain.minimal_expression_model import ProjectionModel
from app.domain.scope_model import ScopeModel
from app.domain.semantics_model import (
    DedupRule,
    FilterInfo,
    JoinInfo,
    MetricInfo,
    ResultGrain,
    RiskInfo,
    SemanticsAnalysisResult,
)


class SemanticsAnalyzer:
    """Analyses query semantics across six dimensions and assembles a caliber report."""

    def analyze(
        self,
        expression_model: ProjectionModel,
        lineage_ir: LineageIR,
        metadata_context: MetadataContext,
        scope_model: ScopeModel,
        parse_result,  # ParseResult with .ast, .sql, .dialect
        source_locations: list[SourceLocation] | None = None,
    ) -> SemanticsAnalysisResult:
        source_locations = source_locations or []
        evidence_pool: list[str] = []

        ast = getattr(parse_result, "ast", None)
        sql_text = getattr(parse_result, "normalized_sql", None) or ""

        # Collect evidence from lineage IR (node/edge IDs)
        for node in lineage_ir.nodes:
            evidence_pool.append(node.id)
        for edge in lineage_ir.edges:
            evidence_pool.append(edge.id)
        for loc in source_locations:
            if loc.location_id:
                evidence_pool.append(loc.location_id)

        # ── 1. Result Grain ──
        result_grain = self._analyze_grain(ast, scope_model, expression_model, evidence_pool)

        # ── 2. Filters ──
        filters = self._analyze_filters(
            ast, scope_model, metadata_context, evidence_pool,
        )

        # ── 3. Metrics ──
        metrics = self._analyze_metrics(expression_model, lineage_ir, evidence_pool)

        # ── 4. Joins ──
        joins = self._analyze_joins(scope_model, lineage_ir, metadata_context, evidence_pool)

        # ── 5. Dedup Logic ──
        dedup_logic = self._analyze_dedup(ast, scope_model, evidence_pool)

        # ── 6. Risks ──
        risks = self._analyze_risks(
            result_grain, filters, metrics, joins, scope_model, expression_model,
            metadata_context, evidence_pool,
        )

        all_evidence = list(dict.fromkeys(evidence_pool))  # deduplicated, order-preserved
        partial = bool(
            result_grain is None
            or result_grain.grain_type == "unknown"
            or any(r.severity == "error" for r in risks)
        )

        return SemanticsAnalysisResult(
            status="partial" if partial else "success",
            result_grain=result_grain,
            filters=filters,
            metrics=metrics,
            joins=joins,
            dedup_logic=dedup_logic,
            semantic_risks=risks,
            evidence_refs=all_evidence,
        )

    # ── Grain Analysis ────────────────────────────────────────────────

    def _analyze_grain(
        self,
        ast,
        scope_model: ScopeModel,
        expression_model: ProjectionModel,
        evidence_pool: list[str],
    ) -> ResultGrain | None:
        if ast is None:
            return ResultGrain(grain_type="unknown")

        group_cols: list[str] = []
        has_windows = False

        # Check for GROUP BY in AST
        group_expr = getattr(ast, "args", {}).get("group")
        if group_expr is not None:
            group_cols = self._extract_groupby_columns(group_expr)
            if group_cols:
                evidence_pool.append("semantics:group_by:detected")
                return ResultGrain(
                    grain_type="group_by",
                    columns=group_cols,
                    evidence_refs=["semantics:group_by:detected"],
                )

        # Check for DISTINCT via sqlglot AST args
        if (
            ast
            and hasattr(ast, "args")
            and isinstance(ast.args.get("distinct"), exp.Distinct)
        ):
            evidence_pool.append("semantics:distinct:detected")
            return ResultGrain(
                grain_type="distinct",
                columns=[
                    p.output_name for p in expression_model.projections
                ] if expression_model.projections else [],
                evidence_refs=["semantics:distinct:detected"],
            )

        # Detect window functions in projections
        for proj in expression_model.projections:
            expr_sql = proj.expression_sql.upper()
            if "OVER (" in expr_sql or "OVER(" in expr_sql:
                has_windows = True
                window_cols = self._extract_partition_by(expr_sql, proj.output_name)
                if window_cols:
                    # Window partition implies grain may be multi-layered
                    pass

        if has_windows:
            evidence_pool.append("semantics:window_partition:detected")
            return ResultGrain(
                grain_type="window_partition",
                columns=[],
                evidence_refs=["semantics:window_partition:detected"],
            )

        # Default: detail (no aggregation / DISTINCT / window)
        evidence_pool.append("semantics:detail:default")
        return ResultGrain(
            grain_type="detail",
            columns=[],
            evidence_refs=["semantics:detail:default"],
        )

    @staticmethod
    def _extract_groupby_columns(group_expr) -> list[str]:
        """Extract column names from a GROUP BY expression node."""
        columns: list[str] = []
        expressions = getattr(group_expr, "expressions", []) or []
        for expr in expressions:
            if isinstance(expr, exp.Column):
                columns.append(expr.name)
            elif isinstance(expr, exp.Literal):
                columns.append(expr.output_name)
            else:
                # Extract column references from complex expressions
                for col in expr.find_all(exp.Column):
                    columns.append(col.name)
        return columns

    @staticmethod
    def _extract_partition_by(expr_sql: str, default_name: str) -> list[str]:
        """Extract PARTITION BY columns from a window function expression SQL."""
        import re
        match = re.search(r"PARTITION\s+BY\s+(.+?)(?:ORDER|ROWS|RANGE|\)\s*$)", expr_sql, re.IGNORECASE)
        if not match:
            return []
        part = match.group(1).strip()
        return [c.strip() for c in part.split(",") if c.strip()]

    # ── Filter Analysis ───────────────────────────────────────────────

    def _analyze_filters(
        self,
        ast,
        scope_model: ScopeModel,
        metadata_context: MetadataContext,
        evidence_pool: list[str],
    ) -> list[FilterInfo]:
        filters: list[FilterInfo] = []
        if ast is None:
            return filters

        # WHERE clause
        where_expr = getattr(ast, "args", {}).get("where")
        if where_expr is not None:
            where_sql = where_expr.sql()
            involved = self._columns_in_expr(where_expr)
            partition_cols = [
                t.columns for t in metadata_context.resolved_tables
                # We can't easily check is_partition without querying the repo
            ]
            # Check if this is a partition filter (looking for 'dt' pattern)
            is_partition_like = any(
                "dt" in c.lower() or "date" in c.lower() or "pt" in c.lower()
                for c in involved
            )
            evidence_pool.append("semantics:where:detected")
            filters.append(
                FilterInfo(
                    filter_type="partition_filter" if is_partition_like else "where",
                    expression=where_sql,
                    involved_columns=involved,
                    evidence_refs=["semantics:where:detected"],
                )
            )

        # HAVING clause
        having_expr = getattr(ast, "args", {}).get("having")
        if having_expr is not None:
            having_sql = having_expr.sql()
            involved = self._columns_in_expr(having_expr)
            evidence_pool.append("semantics:having:detected")
            filters.append(
                FilterInfo(
                    filter_type="having",
                    expression=having_sql,
                    involved_columns=involved,
                    evidence_refs=["semantics:having:detected"],
                )
            )

        # JOIN ON conditions as filters
        for jk in scope_model.join_keys:
            evidence_pool.append("semantics:join_condition:filter")
            filters.append(
                FilterInfo(
                    filter_type="join_condition",
                    expression=jk.raw_sql,
                    involved_columns=[jk.left.column, jk.right.column],
                    evidence_refs=["semantics:join_condition:filter"],
                )
            )

        return filters

    @staticmethod
    def _columns_in_expr(expr) -> list[str]:
        """Extract column names from a sqlglot expression node."""
        columns: list[str] = []
        for col in expr.find_all(exp.Column):
            col_name = f"{col.table}.{col.name}" if col.table else col.name
            columns.append(col_name)
        return columns

    # ── Metric Analysis ───────────────────────────────────────────────

    _AGG_FUNCTIONS = {
        "sum": "sum",
        "count": "count",
        "avg": "avg",
        "min": "min",
        "max": "max",
        "count_distinct": "count_distinct",
    }

    def _analyze_metrics(
        self,
        expression_model: ProjectionModel,
        lineage_ir: LineageIR,
        evidence_pool: list[str],
    ) -> list[MetricInfo]:
        metrics: list[MetricInfo] = []

        for proj in expression_model.projections:
            expr_sql = proj.expression_sql.upper()
            metric_type = "expression"
            target_column = None

            # Detect aggregation function
            for func_name, metric_name in self._AGG_FUNCTIONS.items():
                if func_name.upper() in expr_sql and expr_sql.strip().upper().startswith(
                    func_name.upper() + "("
                ):
                    if func_name == "count" and "DISTINCT" in expr_sql:
                        metric_type = "count_distinct"
                    else:
                        metric_type = metric_name
                    break

            # If not an aggregation, check if it's a plain column reference
            if metric_type == "expression" and proj.expression_kind == "column":
                metric_type = "expression"

            # Find target column from source refs
            if proj.source_refs:
                for ref in proj.source_refs:
                    if ref.column_entity_id:
                        target_column = ref.column_entity_id
                        break

            if metric_type != "expression" or proj.expression_kind in ("function", "expression"):
                evidence_pool.append(proj.output_entity_id)
                metrics.append(
                    MetricInfo(
                        metric_type=metric_type,
                        expression=proj.expression_sql,
                        output_name=proj.output_name,
                        target_column=target_column,
                        evidence_refs=[proj.output_entity_id],
                    )
                )

        return metrics

    # ── Join Analysis ─────────────────────────────────────────────────

    def _analyze_joins(
        self,
        scope_model: ScopeModel,
        lineage_ir: LineageIR,
        metadata_context: MetadataContext,
        evidence_pool: list[str],
    ) -> list[JoinInfo]:
        joins: list[JoinInfo] = []

        # Physical tables (non-CTE)
        physical_tables = [
            r for r in scope_model.relations if not r.is_cte
        ]

        # No joins if only one physical table
        if len(physical_tables) <= 1 and not scope_model.join_keys:
            return joins

        # Build join info from join_keys
        join_keys_per_table: dict[str, JoinInfo] = {}

        for jk in scope_model.join_keys:
            left_table = jk.left.table or "unknown"
            right_table = jk.right.table or "unknown"
            key_expr = f"{jk.left.column} = {jk.right.column}"

            evidence_pool.append("semantics:join:detected")

            # Try to determine join type from key characteristics
            join_type = "inner"  # default assumption for explicit ON clauses
            amplification_risk: str = "none"
            risk_reason = ""

            # Heuristic: if key involves unique columns, risk is lower
            # For now, mark medium risk for any multi-table join
            if len(physical_tables) >= 2:
                amplification_risk = "medium"
                risk_reason = f"多表 JOIN ({len(physical_tables)} 张物理表)，如果关联键不唯一可能导致行数放大"

            # Check for potential cartesian (no join keys)
            if not scope_model.join_keys and len(physical_tables) > 1:
                amplification_risk = "high"
                risk_reason = "多表查询但未检测到 JOIN ON 条件，可能产生笛卡尔积"

            joins.append(
                JoinInfo(
                    join_type=join_type,
                    left_table=left_table,
                    right_table=right_table,
                    join_keys=[key_expr],
                    amplification_risk=amplification_risk,
                    risk_reason=risk_reason,
                    evidence_refs=["semantics:join:detected"],
                )
            )

        return joins

    # ── Dedup Analysis ────────────────────────────────────────────────

    def _analyze_dedup(
        self,
        ast,
        scope_model: ScopeModel,
        evidence_pool: list[str],
    ) -> list[DedupRule]:
        rules: list[DedupRule] = []
        if ast is None:
            return rules

        # SELECT DISTINCT
        if (
            ast
            and hasattr(ast, "args")
            and isinstance(ast.args.get("distinct"), exp.Distinct)
        ):
            evidence_pool.append("semantics:dedup:distinct")
            rules.append(
                DedupRule(
                    dedup_type="distinct",
                    description="SELECT DISTINCT — 去除完全重复的行",
                    evidence_refs=["semantics:dedup:distinct"],
                )
            )

        # GROUP BY (implicit dedup)
        group_expr = getattr(ast, "args", {}).get("group")
        if group_expr is not None:
            evidence_pool.append("semantics:dedup:group_by")
            rules.append(
                DedupRule(
                    dedup_type="group_by",
                    description="GROUP BY — 按分组键隐式去重（每组的聚合结果为一行）",
                    evidence_refs=["semantics:dedup:group_by"],
                )
            )

        # Check projections for ROW_NUMBER and UNION
        from app.domain.minimal_expression_model import ProjectionModel
        for item_sel in getattr(scope_model, "select_items", []):
            expr_sql = getattr(item_sel, "expression_sql", "").upper()
            if "ROW_NUMBER()" in expr_sql:
                evidence_pool.append("semantics:dedup:row_number")
                rules.append(
                    DedupRule(
                        dedup_type="row_number",
                        description=f"ROW_NUMBER() 窗口函数用于去重: {getattr(item_sel, 'expression_sql', '')}",
                        evidence_refs=["semantics:dedup:row_number"],
                    )
                )

        # Union (vs UNION ALL) — implicit dedup
        # Check if AST is a UNION (not UNION ALL)
        if isinstance(ast, exp.Union) and not getattr(ast, "distinct", True):
            # UNION ALL has distinct=False
            pass  # UNION ALL is the default behavior
        elif isinstance(ast, exp.Union):
            evidence_pool.append("semantics:dedup:union")
            rules.append(
                DedupRule(
                    dedup_type="union",
                    description="UNION (非 UNION ALL) — 自动去重合并",
                    evidence_refs=["semantics:dedup:union"],
                )
            )

        return rules

    # ── Risk Analysis ─────────────────────────────────────────────────

    def _analyze_risks(
        self,
        result_grain: ResultGrain | None,
        filters: list[FilterInfo],
        metrics: list[MetricInfo],
        joins: list[JoinInfo],
        scope_model: ScopeModel,
        expression_model: ProjectionModel,
        metadata_context: MetadataContext,
        evidence_pool: list[str],
    ) -> list[RiskInfo]:
        risks: list[RiskInfo] = []

        # 1. Join amplification risk
        for join in joins:
            if join.amplification_risk in ("medium", "high"):
                evidence_pool.append("semantics:risk:join_amplification")
                risks.append(
                    RiskInfo(
                        risk_type="join_amplification",
                        severity="warning" if join.amplification_risk == "medium" else "error",
                        description=join.risk_reason or f"JOIN 关联可能导致行数放大: {join.left_table} ↔ {join.right_table}",
                        evidence_refs=["semantics:risk:join_amplification"],
                    )
                )

        # 2. Grain mixing risk
        if result_grain and result_grain.grain_type == "group_by" and metrics:
            # Check if there are non-aggregated columns in outputs
            has_detail_cols = any(
                p.expression_kind == "column" and p.expression_sql.upper() not in {
                    "SUM(", "COUNT(", "AVG(", "MIN(", "MAX(",
                } and not p.expression_sql.strip().upper().startswith(("SUM(", "COUNT(", "AVG(", "MIN(", "MAX("))
                for p in expression_model.projections
            )
            if not has_detail_cols:
                # All outputs are aggregations or GROUP BY keys — this is fine
                pass

        # 3. No partition filter risk
        has_partition_filter = any(
            f.filter_type == "partition_filter" for f in filters
        )
        physical_tables = [r for r in scope_model.relations if not r.is_cte]
        if physical_tables and not has_partition_filter:
            evidence_pool.append("semantics:risk:no_partition_filter")
            risks.append(
                RiskInfo(
                    risk_type="no_partition_filter",
                    severity="info",
                    description=f"未检测到分区过滤条件（如 dt = 'xxx'），可能触发大表全扫描"
                    if len(physical_tables) <= 2
                    else f"多表查询未检测到分区过滤条件，请注意查询效率",
                    evidence_refs=["semantics:risk:no_partition_filter"],
                )
            )

        # 4. Potential cartesian product
        if len(physical_tables) > 1 and not scope_model.join_keys:
            evidence_pool.append("semantics:risk:potential_cartesian")
            risks.append(
                RiskInfo(
                    risk_type="potential_cartesian",
                    severity="warning",
                    description=f"检测到 {len(physical_tables)} 张表但未发现 JOIN ON 条件，可能产生笛卡尔积",
                    evidence_refs=["semantics:risk:potential_cartesian"],
                )
            )

        # 5. Ambiguous metrics
        ambiguous_metrics = [m for m in metrics if m.target_column is None and m.metric_type != "expression"]
        if ambiguous_metrics:
            evidence_pool.append("semantics:risk:ambiguous_metrics")
            risks.append(
                RiskInfo(
                    risk_type="ambiguous_metrics",
                    severity="info",
                    description=f"{len(ambiguous_metrics)} 个指标表达式缺少明确的源字段追踪",
                    evidence_refs=["semantics:risk:ambiguous_metrics"],
                )
            )

        return risks
