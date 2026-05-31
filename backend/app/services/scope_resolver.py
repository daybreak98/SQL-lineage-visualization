"""P0+M19 ScopeResolver: FROM/JOIN relations, SELECT outputs, WITH CTE detection,
JOIN key extraction, UNION segment tracking, CTE internal column traceback."""

from __future__ import annotations

from sqlglot import exp

from app.diagnostics.collector import DiagnosticsCollector
from app.domain.contracts import Diagnostic, DiagnosticCode, DiagnosticLevel
from app.domain.entity_id import EntityIdFactory
from app.domain.scope_model import (
    ColumnReference,
    JoinKey,
    CteInternalColumn,
    ScopeModel,
    ScopeRelation,
    ScopeSelectItem,
    UnionSegment,
)


class ScopeResolver:
    def resolve(
        self,
        parse_result,
        *,
        default_catalog: str = "default",
        default_schema: str = "default",
    ) -> tuple[ScopeModel, list[Diagnostic]]:
        collector = DiagnosticsCollector()
        scope_id = EntityIdFactory.scope("root")
        model = ScopeModel(scope_id=scope_id)

        ast = parse_result.ast
        if ast is None:
            return model, []

        dialect = parse_result.dialect

        # ── 提取 CTE 定义（WITH 子句）──
        cte_defs: dict[str, exp.CTE] = {}
        cte_names: set[str] = set()
        with_expr = ast.args.get("with")
        if with_expr is not None:
            for cte_expr in getattr(with_expr, "expressions", []) or []:
                cte_alias = getattr(cte_expr, "alias", None)
                if cte_alias:
                    name = cte_alias.lower()
                    cte_names.add(name)
                    cte_defs[name] = cte_expr

        # ── 检测递归 CTE ──
        for cte_name, cte_expr in cte_defs.items():
            if self._is_recursive_cte(cte_expr, cte_name, cte_defs):
                collector.add(
                    DiagnosticCode.RECURSIVE_CTE_UNSUPPORTED,
                    DiagnosticLevel.warning,
                    f"递归 CTE 暂不支持: {cte_name}",
                    suggestion="递归 CTE 的血缘分析将在后续版本支持",
                    related_entity_ids=[scope_id],
                    details={"cte_name": cte_name},
                )

        # ── 提取 CTE 内部字段（M19 增强）──
        for cte_name, cte_expr in cte_defs.items():
            cte_body = getattr(cte_expr, "this", None)
            if cte_body is not None:
                cte_columns = self._extract_cte_internal_columns(
                    cte_body, cte_name, dialect, default_catalog, default_schema,
                )
                model.cte_columns[cte_name] = cte_columns
                model.cte_source_names[cte_name] = [
                    table.name.lower() for table in self._tables_in_select_body(cte_body)
                ]

        # ── 提取 FROM/JOIN 表引用 ──
        seen_aliases: set[str] = set()
        root_tables = self._tables_in_select_body(ast)
        model.cte_source_names["__root__"] = [
            table.name.lower() for table in root_tables
        ]
        # Also extract physical tables from CTE bodies for root scope relations
        if with_expr is not None:
            for cte_expr in getattr(with_expr, "expressions", []) or []:
                cte_body = getattr(cte_expr, "this", None)
                if cte_body is not None:
                    root_tables.extend(self._tables_in_select_body(cte_body))
        for table in root_tables:
            alias = table.alias or table.name
            alias_key = alias.lower()
            if alias_key in seen_aliases:
                collector.add(
                    DiagnosticCode.DUPLICATE_ALIAS,
                    DiagnosticLevel.warning,
                    f"表别名重复: {alias}",
                    suggestion="请为同一作用域内的表使用唯一别名",
                    related_entity_ids=[scope_id],
                    details={"alias": alias},
                )
            seen_aliases.add(alias_key)

            schema = table.db or default_schema
            catalog = table.catalog or default_catalog
            entity_id = EntityIdFactory.table(catalog, schema, table.name)
            is_cte = table.name.lower() in cte_names
            model.relations.append(
                ScopeRelation(
                    relation_id=EntityIdFactory.scope_relation(scope_id, alias),
                    scope_id=scope_id,
                    alias=alias,
                    catalog=catalog,
                    schema=schema,
                    table=table.name,
                    table_entity_id=entity_id,
                    source_name=table.sql(dialect=dialect),
                    is_cte=is_cte,
                )
            )

        # ── 提取 JOIN ON keys（M19 增强）──
        model.join_keys = self._extract_join_keys(ast, dialect)

        # ── 提取 SELECT 输出字段 ──
        # For UNION queries, the root AST is a Union node without expressions;
        # use the leftmost SELECT segment for output columns.
        effective_ast = ast
        if isinstance(ast, (exp.Union, exp.Intersect, exp.Except)):
            effective_ast = self._leftmost_select(ast)
        expressions = getattr(effective_ast, "expressions", []) or []
        for ordinal, expression in enumerate(expressions, start=1):
            model.select_items.append(
                ScopeSelectItem(
                    select_id=f"select:{scope_id}:{ordinal}",
                    scope_id=scope_id,
                    ordinal=ordinal,
                    expression_sql=expression.sql(dialect=dialect),
                    output_name=self._output_name(expression, ordinal),
                    alias=expression.alias or None,
                    expression_kind=self._expression_kind(expression),
                    source_columns=self._column_refs(expression, dialect),
                )
            )

        # ── 提取 UNION segments（M19 增强）──
        model.union_segments = self._extract_union_segments(
            ast, scope_id, dialect, default_catalog, default_schema, cte_names,
        )
        # Add union segment physical tables to root relations (for table-level view)
        for segment in model.union_segments:
            for rel in segment.relations:
                rel_copy = rel.model_copy(update={"scope_id": scope_id})
                # Skip if already present
                existing_ids = {r.relation_id for r in model.relations}
                if rel_copy.relation_id not in existing_ids:
                    model.relations.append(rel_copy)

        return model, collector.list()

    # ── CTE 内部列提取（M19 增强）──
    def _extract_cte_internal_columns(
        self,
        cte_body,
        cte_name: str,
        dialect: str,
        default_catalog: str,
        default_schema: str,
    ) -> list[CteInternalColumn]:
        """Extract output columns and their source column references from a CTE body SELECT."""
        columns: list[CteInternalColumn] = []
        expressions = self._expanded_select_expressions(cte_body)
        for ordinal, expr in enumerate(expressions, start=1):
            output_name = self._output_name(expr, ordinal)
            source_columns = self._column_refs(expr, dialect)
            columns.append(
                CteInternalColumn(
                    cte_name=cte_name,
                    output_name=output_name,
                    ordinal=ordinal,
                    expression_sql=expr.sql(dialect=dialect),
                    source_columns=source_columns,
                    expression_kind=self._expression_kind(expr),
                )
            )
        return columns

    @classmethod
    def _expanded_select_expressions(cls, select_node) -> list:
        """Return SELECT expressions, expanding `SELECT * FROM (SELECT ...)`.

        Real analytics SQL often wraps rich inner SELECTs with a thin
        `SELECT * FROM (...) WHERE ...` layer. Keeping only `*` loses all CTE
        output fields and makes later lineage traversal impossible. This
        method preserves explicit expressions and expands star projections from
        nested subqueries or CTE/table stars when the source shape is available
        in the SQL AST.
        """
        expressions = list(getattr(select_node, "expressions", []) or [])
        if not expressions:
            return expressions

        expanded: list = []
        for expr in expressions:
            if isinstance(expr, exp.Star):
                expanded.extend(cls._star_source_expressions(select_node))
            else:
                expanded.append(expr)
        return expanded or expressions

    @classmethod
    def _star_source_expressions(cls, select_node) -> list:
        from_expr = select_node.args.get("from") or select_node.args.get("from_")
        if from_expr is None or from_expr.this is None:
            return []

        sources = [from_expr.this]
        sources.extend(join.this for join in (select_node.args.get("joins") or []) if join.this is not None)

        expanded: list = []
        for source in sources:
            if isinstance(source, exp.Subquery):
                inner = source.this
                if inner is not None:
                    expanded.extend(cls._expanded_select_expressions(inner))
            elif isinstance(source, exp.Select):
                expanded.extend(cls._expanded_select_expressions(source))
            elif isinstance(source, exp.Table):
                # For CTE/table stars without metadata, expose the table as a
                # relation source. Downstream CTE tracing can match by name.
                expanded.append(exp.column("*", table=source.alias_or_name or source.name))
        return expanded

    # ── 递归 CTE 检测 ──
    @staticmethod
    def _is_recursive_cte(
        cte_expr,
        cte_name: str,
        cte_defs: dict[str, exp.CTE],
    ) -> bool:
        """Check if a CTE references itself directly or through a dependency chain."""
        body = getattr(cte_expr, "this", None)
        if body is None:
            return False
        visited: set[str] = set()
        stack = [body]
        while stack:
            node = stack.pop()
            for table in node.find_all(exp.Table):
                ref_name = table.name.lower()
                if ref_name == cte_name:
                    return True
                if ref_name in cte_defs and ref_name not in visited:
                    visited.add(ref_name)
                    ref_body = getattr(cte_defs[ref_name], "this", None)
                    if ref_body is not None:
                        stack.append(ref_body)
        return False

    # ── JOIN key 提取（M19 增强）──
    @staticmethod
    def _extract_join_keys(
        ast,
        dialect: str,
    ) -> list[JoinKey]:
        """Extract column pairs from JOIN ON clauses."""
        join_keys: list[JoinKey] = []
        for join in ast.args.get("joins") or []:
            on_expr = join.args.get("on")
            if on_expr is None:
                continue
            # Try to extract equi-join column pairs
            if isinstance(on_expr, exp.EQ):
                left_col, right_col = ScopeResolver._eq_columns(on_expr, dialect)
                if left_col and right_col:
                    join_keys.append(
                        JoinKey(
                            left=left_col,
                            right=right_col,
                            raw_sql=on_expr.sql(dialect=dialect),
                        )
                    )
            elif isinstance(on_expr, exp.And):
                for child in on_expr.flatten():
                    if isinstance(child, exp.EQ):
                        left_col, right_col = ScopeResolver._eq_columns(child, dialect)
                        if left_col and right_col:
                            join_keys.append(
                                JoinKey(
                                    left=left_col,
                                    right=right_col,
                                    raw_sql=child.sql(dialect=dialect),
                                )
                            )
        return join_keys

    @staticmethod
    def _eq_columns(eq_node, dialect: str) -> tuple[ColumnReference | None, ColumnReference | None]:
        """Extract column references from both sides of an equality expression."""
        left = eq_node.left
        right = eq_node.right
        left_col = None
        right_col = None
        if isinstance(left, exp.Column):
            left_col = ColumnReference(
                raw=left.sql(dialect=dialect),
                column=left.name,
                table=left.table or None,
                schema=left.db or None,
                catalog=left.catalog or None,
            )
        if isinstance(right, exp.Column):
            right_col = ColumnReference(
                raw=right.sql(dialect=dialect),
                column=right.name,
                table=right.table or None,
                schema=right.db or None,
                catalog=right.catalog or None,
            )
        return left_col, right_col

    # ── UNION 辅助方法 ──
    @staticmethod
    def _leftmost_select(ast):
        """Walk down the Union/Intersect/Except chain to find the leftmost SELECT."""
        if isinstance(ast, (exp.Union, exp.Intersect, exp.Except)):
            left = ast.args.get("expression") or getattr(ast, "left", None)
            if left is not None:
                return ScopeResolver._leftmost_select(left)
        return ast

    # ── UNION segment 提取（M19 增强）──
    def _extract_union_segments(
        self,
        ast,
        scope_id: str,
        dialect: str,
        default_catalog: str,
        default_schema: str,
        cte_names: set[str],
    ) -> list[UnionSegment]:
        """Extract individual UNION/UNION ALL segments with their relations and select items."""
        segments: list[UnionSegment] = []

        # Check if this is a UNION type query (SetOperation)
        # sqlglot represents UNION as `exp.Union` or `exp.SetOperation`
        if not isinstance(ast, (exp.Union, exp.Intersect, exp.Except)):
            # For simple queries, check if there's a union in args
            union_type = ast.args.get("union")
            if union_type is not None:
                # This is a union chain
                return self._extract_chain_union_segments(
                    ast, scope_id, dialect, default_catalog, default_schema, cte_names,
                )

        # For multi-segment UNION: iterate left/right
        if isinstance(ast, (exp.Union, exp.Intersect, exp.Except)):
            idx = 1
            current = ast
            while isinstance(current, (exp.Union, exp.Intersect, exp.Except)):
                # Right side is one segment
                right = getattr(current, "this", None)
                if right is not None:
                    segment = self._build_union_segment(
                        right, scope_id, dialect, default_catalog, default_schema, cte_names, idx,
                    )
                    segments.append(segment)
                    idx += 1
                # Walk to left side
                left = getattr(current, "expression", None)
                if left is None and hasattr(current, "left"):
                    left = current.left
                if left is None:
                    break
                if isinstance(left, (exp.Union, exp.Intersect, exp.Except)):
                    current = left
                else:
                    # Last segment (leftmost)
                    segment = self._build_union_segment(
                        left, scope_id, dialect, default_catalog, default_schema, cte_names, idx,
                    )
                    segments.append(segment)
                    break

        return segments

    def _extract_chain_union_segments(
        self,
        ast,
        scope_id: str,
        dialect: str,
        default_catalog: str,
        default_schema: str,
        cte_names: set[str],
    ) -> list[UnionSegment]:
        """Handle UNION as an attribute chain (sqlglot v20+)."""
        segments: list[UnionSegment] = []
        union_expr = ast.args.get("union")
        # This is more complex - the chain is represented differently
        # For now, just extract all physical tables from the union
        # The union field in sqlglot v20+ is a bool, not the actual union
        return segments

    def _build_union_segment(
        self,
        segment_ast,
        scope_id: str,
        dialect: str,
        default_catalog: str,
        default_schema: str,
        cte_names: set[str],
        segment_index: int,
    ) -> UnionSegment:
        """Build a UnionSegment from a single UNION member SELECT."""
        # Extract relations
        relations: list[ScopeRelation] = []
        for table in self._tables_in_select_body(segment_ast):
            alias = table.alias or table.name
            schema = table.db or default_schema
            catalog = table.catalog or default_catalog
            entity_id = EntityIdFactory.table(catalog, schema, table.name)
            is_cte = table.name.lower() in cte_names
            relations.append(
                ScopeRelation(
                    relation_id=EntityIdFactory.scope_relation(scope_id, alias),
                    scope_id=scope_id,
                    alias=alias,
                    catalog=catalog,
                    schema=schema,
                    table=table.name,
                    table_entity_id=entity_id,
                    source_name=table.sql(dialect=dialect),
                    is_cte=is_cte,
                )
            )

        # Extract select items
        select_items: list[ScopeSelectItem] = []
        expressions = getattr(segment_ast, "expressions", []) or []
        for ordinal, expression in enumerate(expressions, start=1):
            select_items.append(
                ScopeSelectItem(
                    select_id=f"select:{scope_id}:union{segment_index}:{ordinal}",
                    scope_id=scope_id,
                    ordinal=ordinal,
                    expression_sql=expression.sql(dialect=dialect),
                    output_name=self._output_name(expression, ordinal),
                    alias=expression.alias or None,
                    expression_kind=self._expression_kind(expression),
                    source_columns=self._column_refs(expression, dialect),
                )
            )

        return UnionSegment(
            segment_index=segment_index,
            relations=relations,
            select_items=select_items,
            raw_sql=segment_ast.sql(dialect=dialect),
        )

    # ── 改进的表提取方法 ──
    @staticmethod
    def _tables_in_select_body(ast) -> list[exp.Table]:
        """Extract all physical tables referenced in FROM/JOIN of a SELECT body.
        Renamed from _tables_in_root_scope for clarity."""
        tables: list[exp.Table] = []
        # Root query FROM/JOIN
        from_expr = ast.args.get("from") or ast.args.get("from_")
        if from_expr is not None:
            inner = from_expr.this
            if isinstance(inner, exp.Table):
                tables.append(inner)
            elif isinstance(inner, (exp.Select, exp.Subquery)):
                # FROM 子查询：递归提取子查询体中的物理表
                sub_ast = inner.this if isinstance(inner, exp.Subquery) else inner
                if sub_ast is not None:
                    tables.extend(ScopeResolver._tables_in_select_body(sub_ast))
        for join in ast.args.get("joins") or []:
            inner = join.this
            if isinstance(inner, exp.Table):
                tables.append(inner)
            elif isinstance(inner, (exp.Select, exp.Subquery)):
                sub_ast = inner.this if isinstance(inner, exp.Subquery) else inner
                if sub_ast is not None:
                    tables.extend(ScopeResolver._tables_in_select_body(sub_ast))
        return tables

    # ── 保留兼容旧方法名 ──
    @staticmethod
    def _tables_in_root_scope(ast) -> list[exp.Table]:
        """Backward-compatible alias for _tables_in_select_body."""
        return ScopeResolver._tables_in_select_body(ast)

    @staticmethod
    def _output_name(expression, ordinal: int) -> str:
        output = getattr(expression, "output_name", "") or expression.alias_or_name
        return output or f"expr_{ordinal}"

    @staticmethod
    def _expression_kind(expression) -> str:
        inner = expression.this if isinstance(expression, exp.Alias) else expression
        if isinstance(inner, exp.Column):
            return "column"
        if isinstance(inner, exp.Literal):
            return "literal"
        if isinstance(inner, (exp.Func, exp.Cast, exp.TryCast, exp.Coalesce)):
            return "function"
        return "expression"

    @staticmethod
    def _column_refs(expression, dialect: str) -> list[ColumnReference]:
        refs: list[ColumnReference] = []
        for column in expression.find_all(exp.Column):
            refs.append(
                ColumnReference(
                    raw=column.sql(dialect=dialect),
                    column=column.name,
                    table=column.table or None,
                    schema=column.db or None,
                    catalog=column.catalog or None,
                )
            )
        return refs
