"""M23 (R13a) ExpressionAnalyzer: identifies aggregate / CASE WHEN / window functions
and extracts source column dependencies."""

from __future__ import annotations

from sqlglot import exp

from app.domain.expression_model import (
    AggregateExpression,
    CaseBranch,
    CaseWhenExpression,
    ExpressionModel,
    WindowFunction,
)
from app.domain.minimal_expression_model import ProjectionModel
from app.domain.scope_model import ColumnReference, ScopeModel


# ── known aggregate function names (sqlglot class → friendly name) ──
_AGGREGATE_NAMES: dict[type, str] = {
    exp.Sum: "SUM",
    exp.Count: "COUNT",
    exp.Avg: "AVG",
    exp.Max: "MAX",
    exp.Min: "MIN",
    exp.Variance: "VARIANCE",
    exp.VariancePop: "VARIANCE_POP",
    exp.ApproxDistinct: "APPROX_DISTINCT",
    exp.GroupConcat: "GROUP_CONCAT",
}

# ── known window / ranking function names ──
_WINDOW_FUNCTION_NAMES: set[str] = {
    "ROW_NUMBER", "RANK", "DENSE_RANK", "PERCENT_RANK", "CUME_DIST",
    "NTILE", "LEAD", "LAG", "FIRST_VALUE", "LAST_VALUE", "NTH_VALUE",
}


class ExpressionAnalyzer:
    """Walks the sqlglot AST from a parsed query and classifies each SELECT
    expression as an aggregate, CASE WHEN, or window function, extracting
    the source column references for each."""

    def analyze(
        self,
        parse_result,
        projection_model: ProjectionModel,
        scope_model: ScopeModel,
    ) -> ExpressionModel:
        ast = parse_result.ast
        dialect = parse_result.dialect
        if ast is None:
            return ExpressionModel()

        model = ExpressionModel()
        expressions = getattr(ast, "expressions", []) or []

        for ordinal, expr_node in enumerate(expressions, start=1):
            # Unwrap Alias to get the inner expression
            inner = expr_node.this if isinstance(expr_node, exp.Alias) else expr_node

            if self._is_window(inner):
                wf = self._build_window(inner, scope_model.scope_id, ordinal, dialect)
                model.window_functions.append(wf)
                continue

            if self._has_case(inner):
                cw = self._build_case_when(inner, scope_model.scope_id, ordinal, dialect)
                model.case_whens.append(cw)
                continue

            if self._is_aggregate(inner):
                agg = self._build_aggregate(inner, scope_model.scope_id, ordinal, dialect)
                model.aggregates.append(agg)
                continue

            # Expression not classified → no specialised expression node needed;
            # the P0 projection already handles simple column / literal / function refs.

        return model

    # ── detection helpers ──────────────────────────────────────────────

    @staticmethod
    def _is_window(node: exp.Expression) -> bool:
        return isinstance(node, exp.Window) or any(
            isinstance(child, exp.Window) for child in node.walk()
        )

    @staticmethod
    def _has_case(node: exp.Expression) -> bool:
        if isinstance(node, exp.Case):
            return True
        # walk children but skip nested Window nodes
        return any(isinstance(child, exp.Case) for child in node.walk()
                   if not isinstance(child, exp.Window))

    @staticmethod
    def _is_aggregate(node: exp.Expression) -> bool:
        return isinstance(node, exp.AggFunc) or any(
            isinstance(child, exp.AggFunc) for child in node.walk()
        )

    # ── builders ───────────────────────────────────────────────────────

    def _build_aggregate(
        self,
        node: exp.Expression,
        scope_id: str,
        ordinal: int,
        dialect: str,
    ) -> AggregateExpression:
        # Find the outermost aggregate
        agg_node = node if isinstance(node, exp.AggFunc) else self._first_agg(node)
        func_name = self._agg_name(agg_node) if agg_node else "UNKNOWN_AGG"
        is_distinct = self._has_distinct(agg_node) if agg_node else False
        args_sql = self._args_sql(agg_node, dialect) if agg_node else None
        source_cols = self._extract_columns(agg_node or node, dialect)
        return AggregateExpression(
            expression_id=f"expression:{scope_id}:{ordinal}:agg",
            scope_id=scope_id,
            ordinal=ordinal,
            function_name=func_name,
            expression_sql=node.sql(dialect=dialect),
            source_columns=source_cols,
            is_distinct=is_distinct,
            args_sql=args_sql,
        )

    def _build_case_when(
        self,
        node: exp.Expression,
        scope_id: str,
        ordinal: int,
        dialect: str,
    ) -> CaseWhenExpression:
        case_node = node if isinstance(node, exp.Case) else self._first_case(node)
        branches: list[CaseBranch] = []
        all_source_cols: list[ColumnReference] = []

        if case_node:
            ifs = getattr(case_node, "ifs", None) or case_node.args.get("ifs") or []
            for if_expr in ifs:
                cond_sql = if_expr.this.sql(dialect=dialect) if if_expr.this else ""
                value_sql = if_expr.args.get("true")
                value_sql = value_sql.sql(dialect=dialect) if value_sql else ""
                branch_cols = self._extract_columns(if_expr, dialect)
                branches.append(CaseBranch(
                    condition_sql=cond_sql,
                    value_sql=value_sql,
                    source_columns=branch_cols,
                ))
                all_source_cols.extend(branch_cols)

            default = case_node.args.get("default")
            default_sql = default.sql(dialect=dialect) if default else None
        else:
            default_sql = None

        # Also extract any columns from the whole expression (e.g. simple CASE)
        expr_cols = self._extract_columns(node, dialect)
        all_source_cols.extend(expr_cols)

        return CaseWhenExpression(
            expression_id=f"expression:{scope_id}:{ordinal}:case",
            scope_id=scope_id,
            ordinal=ordinal,
            expression_sql=node.sql(dialect=dialect),
            branches=branches,
            default_value_sql=default_sql,
            source_columns=self._dedupe_cols(all_source_cols),
        )

    def _build_window(
        self,
        node: exp.Expression,
        scope_id: str,
        ordinal: int,
        dialect: str,
    ) -> WindowFunction:
        win_node = node if isinstance(node, exp.Window) else self._first_window(node)
        func_name = "UNKNOWN"
        partition_cols: list[ColumnReference] = []
        order_cols: list[ColumnReference] = []

        if win_node:
            inner = win_node.this
            func_name = self._window_func_name(inner) if inner else "UNKNOWN"

            # PARTITION BY
            partition = win_node.args.get("partition") or []
            if isinstance(partition, exp.Expression):
                partition = [partition]
            for part in (partition if isinstance(partition, list) else []):
                partition_cols.extend(self._extract_columns(part, dialect))

            # ORDER BY
            order = win_node.args.get("order")
            if order:
                if isinstance(order, exp.Order):
                    for ordered in order.expressions:
                        order_cols.extend(self._extract_columns(ordered, dialect))
                elif isinstance(order, list):
                    for o in order:
                        order_cols.extend(self._extract_columns(o, dialect))

        source_cols = self._extract_columns(node, dialect)

        return WindowFunction(
            expression_id=f"expression:{scope_id}:{ordinal}:window",
            scope_id=scope_id,
            ordinal=ordinal,
            function_name=func_name,
            expression_sql=node.sql(dialect=dialect),
            partition_by_columns=self._dedupe_cols(partition_cols),
            order_by_columns=self._dedupe_cols(order_cols),
            source_columns=self._dedupe_cols(source_cols),
        )

    # ── AST traversal helpers ──────────────────────────────────────────

    @staticmethod
    def _first_agg(node: exp.Expression) -> exp.Expression | None:
        for child in node.walk():
            if isinstance(child, exp.AggFunc):
                return child
        return None

    @staticmethod
    def _first_case(node: exp.Expression) -> exp.Expression | None:
        for child in node.walk():
            if isinstance(child, exp.Case):
                return child
        return None

    @staticmethod
    def _first_window(node: exp.Expression) -> exp.Expression | None:
        for child in node.walk():
            if isinstance(child, exp.Window):
                return child
        return None

    @staticmethod
    def _agg_name(agg_node: exp.Expression) -> str:
        """Return the friendly aggregate name, including COUNT_DISTINCT."""
        for cls, name in _AGGREGATE_NAMES.items():
            if isinstance(agg_node, cls):
                if isinstance(agg_node, exp.Count) and ExpressionAnalyzer._has_distinct(agg_node):
                    return "COUNT_DISTINCT"
                return name
        return agg_node.__class__.__name__.upper()

    @staticmethod
    def _has_distinct(node: exp.Expression) -> bool:
        """Check whether an aggregate (COUNT) uses DISTINCT."""
        for child in node.find_all(exp.Distinct):
            return True
        # Also check the args for a 'distinct' key
        return bool(node.args.get("distinct"))

    @staticmethod
    def _args_sql(node: exp.Expression, dialect: str) -> str | None:
        """Return the SQL representation of the aggregate's arguments (excluding the function name)."""
        exprs = getattr(node, "expressions", None)
        if exprs is None:
            exprs = node.args.get("expressions") or []
        if not exprs:
            return None
        return ", ".join(e.sql(dialect=dialect) for e in exprs)

    @staticmethod
    def _window_func_name(inner: exp.Expression) -> str:
        """Determine the function name inside a Window."""
        # Check if it's a named window function like ROW_NUMBER, RANK, etc.
        if isinstance(inner, exp.Anonymous):
            name = inner.name.upper() if inner.name else "UNKNOWN"
            return name
        # Check if it's a known aggregate
        for cls, name in _AGGREGATE_NAMES.items():
            if isinstance(inner, cls):
                return name
        # Fallback
        sql_name = inner.sql(dialect="spark").split("(")[0].strip().upper()
        return sql_name or inner.__class__.__name__.upper()

    # ── column extraction ──────────────────────────────────────────────

    @staticmethod
    def _extract_columns(node: exp.Expression, dialect: str) -> list[ColumnReference]:
        refs: list[ColumnReference] = []
        for column in node.find_all(exp.Column):
            refs.append(ColumnReference(
                raw=column.sql(dialect=dialect),
                column=column.name,
                table=column.table or None,
                schema=column.db or None,
                catalog=column.catalog or None,
            ))
        return refs

    @staticmethod
    def _dedupe_cols(cols: list[ColumnReference]) -> list[ColumnReference]:
        seen: set[tuple[str | None, str]] = set()
        result: list[ColumnReference] = []
        for c in cols:
            key = (c.table.lower() if c.table else None, c.column.lower())
            if key not in seen:
                seen.add(key)
                result.append(c)
        return result
