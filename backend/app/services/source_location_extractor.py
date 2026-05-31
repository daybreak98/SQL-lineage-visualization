"""M18+M24 SourceLocation 精准提取。

M18 (R09b1): select/from/where/group by/order by 中的字段、表、别名位置。
M24 (R09b2): CTE 定义、子查询、JOIN ON、UNION 段、CASE WHEN、窗口函数位置。

核心策略：
1. 使用 sqlglot tokenizer 获取 token 级别的精确位置（字符偏移）
2. 将 token 偏移转换为 UTF-16 偏移（Monaco 编辑器兼容）
3. 对 AST 节点，通过 token text 匹配找到对应位置
4. 对复杂表达式无法直接通过 token 定位的，使用文本子串搜索降级
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp

from app.domain.contracts import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticLevel,
    EntityType,
    SourceLocation,
)
from app.domain.entity_id import EntityIdFactory, hash_name
from app.domain.name_resolution_model import (
    NameResolutionResult,
    ResolvedColumnRef,
)
from app.domain.scope_model import ColumnReference, ScopeModel
from app.utils.text_coordinates import (
    python_index_to_utf16_offset,
    source_sql_id,
    utf16_code_units,
    utf16_offset_to_line_col,
    utf16_range_for_text,
)


class SourceLocationExtractor:
    """从原始 SQL 中提取实体（字段/表/别名）的精准位置信息。

    输入 original_sql + ParseResult + ScopeModel + NameResolutionResult，
    输出 (list[SourceLocation], list[Diagnostic])。
    """

    def extract(
        self,
        original_sql: str,
        parse_result,
        scope_model: ScopeModel,
        name_resolution: NameResolutionResult,
    ) -> tuple[list[SourceLocation], list[Diagnostic]]:
        """返回 (source_locations, diagnostics)。"""
        locations: list[SourceLocation] = []
        diagnostics: list[Diagnostic] = []
        ast = getattr(parse_result, "ast", None)
        dialect = getattr(parse_result, "dialect", "spark")
        if ast is None:
            return locations, diagnostics

        sql_id = source_sql_id(original_sql)

        # 建立 resolved column 查找表
        resolved_col_by_ref = _build_resolved_column_lookup(
            name_resolution.resolved_columns
        )

        # ── 1. SELECT 字段定位 ──
        self._extract_select_item_locations(
            locations, original_sql, sql_id, scope_model,
            resolved_col_by_ref, name_resolution,
        )

        # ── 2. FROM 表定位 ──
        self._extract_relation_locations(
            locations, original_sql, sql_id, scope_model,
        )

        # ── 3. WHERE 子句字段定位 ──
        self._extract_clause_locations(
            locations, diagnostics, original_sql, sql_id, ast, "where",
            scope_model, resolved_col_by_ref, name_resolution, dialect,
        )

        # ── 4. GROUP BY 子句字段定位 ──
        self._extract_clause_locations(
            locations, diagnostics, original_sql, sql_id, ast, "group",
            scope_model, resolved_col_by_ref, name_resolution, dialect,
        )

        # ── 5. ORDER BY 子句字段定位 ──
        self._extract_clause_locations(
            locations, diagnostics, original_sql, sql_id, ast, "order",
            scope_model, resolved_col_by_ref, name_resolution, dialect,
        )

        # ══════════════════════════════════════════════════════════════════
        # M24 (R09b2) 增强: CTE/子查询/JOIN/UNION/CASE WHEN/窗口函数
        # ══════════════════════════════════════════════════════════════════

        # ── 6. CTE 定义位置 ──
        self._extract_cte_definition_locations(
            locations, original_sql, sql_id, ast, dialect,
        )

        # ── 7. 子查询位置 ──
        self._extract_subquery_locations(
            locations, original_sql, sql_id, ast, dialect,
        )

        # ── 8. JOIN ON 条件位置 ──
        self._extract_join_on_locations(
            locations, original_sql, sql_id, ast, dialect,
        )

        # ── 9. UNION 段位置 ──
        self._extract_union_locations(
            locations, original_sql, sql_id, scope_model,
        )

        # ── 10. CASE WHEN 位置 ──
        self._extract_case_when_locations(
            locations, original_sql, sql_id, ast, dialect,
        )

        # ── 11. 窗口函数位置 ──
        self._extract_window_locations(
            locations, original_sql, sql_id, ast, dialect,
        )

        return locations, diagnostics

    # ------------------------------------------------------------------
    # 1. SELECT 字段定位
    # ------------------------------------------------------------------

    def _extract_select_item_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        scope_model: ScopeModel,
        resolved_col_by_ref: dict,
        name_resolution: NameResolutionResult,
    ) -> None:
        """定位 SELECT 列表中的每个表达式的坐标。"""
        for item in scope_model.select_items:
            output_entity_id = EntityIdFactory.output_column(
                item.scope_id, item.output_name, item.ordinal,
            )
            # 定位整个 select 表达式文本
            expr_loc = self._make_location(
                sql, sql_id, item.expression_sql,
                entity_id=output_entity_id,
                entity_type=EntityType.output_column,
                confidence=0.9,
            )
            locations.append(expr_loc)

            # 如果有别名，定位别名文本
            if item.alias and item.alias.lower() != item.output_name.lower():
                alias_loc = self._make_location(
                    sql, sql_id, item.alias,
                    entity_id=output_entity_id,
                    entity_type=EntityType.output_column,
                    confidence=0.95,
                )
                locations.append(alias_loc)

            # 定位 select 表达式中的 source_columns
            for ref in item.source_columns:
                entity_id, entity_type = self._match_column_ref(
                    ref, scope_model, resolved_col_by_ref, name_resolution,
                )
                col_loc = self._make_location(
                    sql, sql_id, ref.raw,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    confidence=0.85,
                )
                locations.append(col_loc)

    # ------------------------------------------------------------------
    # 2. FROM 表定位
    # ------------------------------------------------------------------

    def _extract_relation_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        scope_model: ScopeModel,
    ) -> None:
        """定位 FROM/JOIN 中的表引用坐标。"""
        for rel in scope_model.relations:
            # 定位表全限定名
            table_text = rel.table
            if rel.schema and rel.schema != "default":
                table_text = f"{rel.schema}.{table_text}"
            if rel.catalog and rel.catalog != "default":
                table_text = f"{rel.catalog}.{table_text}"

            full_loc = self._make_location(
                sql, sql_id, table_text,
                entity_id=rel.table_entity_id,
                entity_type=EntityType.table,
                confidence=0.95,
            )
            locations.append(full_loc)

            # 定位表别名（如果不同于表名）
            if rel.alias and rel.alias.lower() != rel.table.lower():
                alias_loc = self._make_location(
                    sql, sql_id, rel.alias,
                    entity_id=rel.table_entity_id,
                    entity_type=EntityType.table_alias,
                    confidence=0.9,
                )
                locations.append(alias_loc)

    # ------------------------------------------------------------------
    # 3-5. WHERE / GROUP BY / ORDER BY 字段定位
    # ------------------------------------------------------------------

    def _extract_clause_locations(
        self,
        locations: list[SourceLocation],
        diagnostics: list[Diagnostic],
        sql: str,
        sql_id: str,
        ast,
        clause: str,
        scope_model: ScopeModel,
        resolved_col_by_ref: dict,
        name_resolution: NameResolutionResult,
        dialect: str,
    ) -> None:
        """从 WHERE / GROUP BY / ORDER BY 中提取列引用位置。"""
        clause_exp = _find_clause(ast, clause)
        if clause_exp is None:
            return

        for col in clause_exp.find_all(exp.Column):
            raw_text = col.sql(dialect=dialect)
            if not raw_text:
                continue

            ref = ColumnReference(
                raw=raw_text,
                column=col.name,
                table=col.table or None,
                schema=col.db or None,
                catalog=col.catalog or None,
            )
            entity_id, entity_type = self._match_column_ref(
                ref, scope_model, resolved_col_by_ref, name_resolution,
            )

            loc = self._make_location(
                sql, sql_id, raw_text,
                entity_id=entity_id,
                entity_type=entity_type,
                confidence=0.85,
            )
            locations.append(loc)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _make_location(
        sql: str,
        sql_id: str,
        raw_text: str,
        *,
        entity_id: str,
        entity_type: EntityType,
        confidence: float = 0.9,
    ) -> SourceLocation:
        """在原始 SQL 中搜索文本并构建 SourceLocation。

        如果找不到精确位置，返回 unavailable。
        """
        if not raw_text:
            return _unavailable_location(
                entity_id=entity_id,
                entity_type=entity_type,
                sql_id=sql_id,
                raw_text=raw_text,
            )

        found = utf16_range_for_text(sql, raw_text)
        if found is None:
            return _unavailable_location(
                entity_id=entity_id,
                entity_type=entity_type,
                sql_id=sql_id,
                raw_text=raw_text,
            )

        start_utf16, end_utf16 = found
        start_line, start_col = utf16_offset_to_line_col(sql, start_utf16)
        end_line, end_col = utf16_offset_to_line_col(sql, end_utf16)
        return SourceLocation(
            location_id=(
                f"loc:{hash_name(entity_id + ':' + str(start_utf16) + ':' + str(end_utf16))}"
            ),
            entity_id=entity_id,
            entity_type=entity_type,
            source_sql_id=sql_id,
            range_type="exact" if confidence >= 0.8 else "synthetic",
            start_line=start_line,
            start_col=start_col,
            end_line=end_line,
            end_col=end_col,
            start_offset=start_utf16,
            end_offset=end_utf16,
            raw_text=raw_text,
            confidence=confidence,
        )

    @staticmethod
    def _match_column_ref(
        ref: ColumnReference,
        scope_model: ScopeModel,
        resolved_col_by_ref: dict,
        name_resolution: NameResolutionResult,
    ) -> tuple[str, EntityType]:
        """根据 ColumnReference 匹配 entity_id 和 entity_type。"""
        col_key = (
            ref.table.lower() if ref.table else None,
            ref.column.lower(),
        )

        # 先在 resolved_columns 中匹配
        resolved = resolved_col_by_ref.get(col_key)
        if resolved:
            return resolved.column_entity_id, EntityType.column

        # 尝试在 unresolved_columns 中匹配
        for unres in name_resolution.unresolved_columns:
            uref = unres.reference
            if uref.column.lower() == col_key[1]:
                if col_key[0] is None or (
                    uref.table and uref.table.lower() == col_key[0]
                ):
                    return (
                        EntityIdFactory.scope_column(
                            scope_model.scope_id,
                            uref.table or "unknown",
                            uref.column,
                        ),
                        EntityType.column,
                    )

        # 默认使用 scope_column entity_id
        col_name = col_key[1]
        tbl_key = col_key[0] or "unknown"
        return (
            EntityIdFactory.scope_column(scope_model.scope_id, tbl_key, col_name),
            EntityType.column,
        )

    # ══════════════════════════════════════════════════════════════════════
    # M24 (R09b2) 增强方法
    # ══════════════════════════════════════════════════════════════════════

    # ── 6. CTE 定义位置 ─────────────────────────────────────────────────

    def _extract_cte_definition_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        ast,
        dialect: str,
    ) -> None:
        """定位 WITH 子句中每个 CTE 定义的 start/end 行位置。"""
        with_expr = ast.args.get("with") if ast else None
        if with_expr is None:
            return

        cte_exprs = getattr(with_expr, "expressions", []) or []
        scope_id = "scope:root"

        # 1) 定位 WITH 关键字整体 range
        with_text = with_expr.sql(dialect=dialect)
        with_loc = self._make_location(
            sql, sql_id, with_text,
            entity_id=f"with:{scope_id}",
            entity_type=EntityType.cte,
            confidence=0.85,
        )
        locations.append(with_loc)

        # 2) 逐个定位 CTE 定义
        for cte_expr in cte_exprs:
            cte_alias = getattr(cte_expr, "alias", None)
            if cte_alias is None:
                continue
            cte_name = cte_alias.lower()
            entity_id = f"cte:{scope_id}:{cte_name}"

            cte_body = getattr(cte_expr, "this", None)
            if cte_body is None:
                continue

            # 搜索 CTE 定义文本: "{name} AS (SELECT ...)"
            cte_sql = cte_expr.sql(dialect=dialect)
            loc = self._make_location(
                sql, sql_id, cte_sql,
                entity_id=entity_id,
                entity_type=EntityType.cte,
                confidence=0.85,
            )
            if loc.range_type == "unavailable":
                # 降级: 按行搜索 CTE 名 + AS
                loc = self._locate_cte_by_name(sql, sql_id, entity_id, cte_name)
            locations.append(loc)

    @staticmethod
    def _locate_cte_by_name(
        sql: str, sql_id: str, entity_id: str, cte_name: str,
    ) -> SourceLocation:
        """降级方案: 通过 CTE 名称搜索定义行范围。"""
        import re
        # 搜索 "{cte_name} AS (" 模式（大小写不敏感）
        pattern = re.compile(
            rf'(?:^|\W)({re.escape(cte_name)})\s+AS\s*\(', re.IGNORECASE
        )
        match = pattern.search(sql)
        if match is None:
            return _unavailable_location(
                entity_id=entity_id,
                entity_type=EntityType.cte,
                sql_id=sql_id,
                raw_text=cte_name,
            )
        start_idx = match.start(1)
        start_utf16 = python_index_to_utf16_offset(sql, start_idx)
        start_line, start_col = utf16_offset_to_line_col(sql, start_utf16)
        # end 设为同一行末（近似）
        line_end_idx = sql.find("\n", match.end())
        if line_end_idx < 0:
            line_end_idx = len(sql)
        end_utf16 = python_index_to_utf16_offset(sql, line_end_idx)
        end_line, end_col = utf16_offset_to_line_col(sql, end_utf16)
        return SourceLocation(
            location_id=f"loc:{hash_name(entity_id + ':' + str(start_utf16) + ':' + str(end_utf16))}",
            entity_id=entity_id,
            entity_type=EntityType.cte,
            source_sql_id=sql_id,
            range_type="exact",
            start_line=start_line,
            start_col=start_col,
            end_line=end_line,
            end_col=end_col,
            start_offset=start_utf16,
            end_offset=end_utf16,
            raw_text=cte_name,
            confidence=0.75,
        )

    # ── 7. 子查询位置 ────────────────────────────────────────────────

    def _extract_subquery_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        ast,
        dialect: str,
    ) -> None:
        """定位 FROM / JOIN 中的子查询 range。"""
        scope_id = "scope:root"
        idx = 0

        # 收集所有子查询 AST 节点
        subquery_nodes: list[exp.Expression] = []

        def _collect_subqueries(node):
            if node is None:
                return
            if isinstance(node, exp.Subquery):
                subquery_nodes.append(node)
                return
            if isinstance(node, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
                return  # 不递归进子句的 SELECT 避免与根混淆
            for child in node.iter_expressions():
                _collect_subqueries(child)

        # 收集 FROM 中的子查询
        from_expr = ast.args.get("from") if ast else None
        if from_expr is not None:
            from_inner = from_expr.this
            if isinstance(from_inner, exp.Subquery):
                subquery_nodes.append(from_inner)
            elif isinstance(from_inner, exp.Select):
                subquery_nodes.append(exp.Subquery(this=from_inner))

        # 收集 JOIN 中的子查询
        for join in (ast.args.get("joins") or []) if ast else []:
            join_inner = getattr(join, "this", None)
            if join_inner is not None:
                if isinstance(join_inner, exp.Subquery):
                    subquery_nodes.append(join_inner)
                elif isinstance(join_inner, exp.Select):
                    subquery_nodes.append(exp.Subquery(this=join_inner))

        for sq_node in subquery_nodes:
            idx += 1
            entity_id = f"subquery:{scope_id}:{idx}"
            raw_sql = sq_node.sql(dialect=dialect)
            loc = self._make_location(
                sql, sql_id, raw_sql,
                entity_id=entity_id,
                entity_type=EntityType.subquery,
                confidence=0.8,
            )
            locations.append(loc)

    # ── 8. JOIN ON 条件位置 ────────────────────────────────────────────

    def _extract_join_on_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        ast,
        dialect: str,
    ) -> None:
        """定位每个 JOIN 的 ON 子句 range。"""
        scope_id = "scope:root"
        joins = (ast.args.get("joins") or []) if ast else []
        for j_idx, join_node in enumerate(joins, start=1):
            on_expr = join_node.args.get("on")
            if on_expr is None:
                continue
            entity_id = f"join_on:{scope_id}:{j_idx}"
            on_sql = on_expr.sql(dialect=dialect)
            loc = self._make_location(
                sql, sql_id, on_sql,
                entity_id=entity_id,
                entity_type=EntityType.join,
                confidence=0.85,
            )
            locations.append(loc)

    # ── 9. UNION 段位置 ─────────────────────────────────────────────────

    def _extract_union_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        scope_model: ScopeModel,
    ) -> None:
        """定位 UNION ALL 各段的 SELECT 起止位置。"""
        for segment in scope_model.union_segments:
            if not segment.raw_sql:
                continue
            entity_id = f"union_segment:{scope_model.scope_id}:{segment.segment_index}"
            loc = self._make_location(
                sql, sql_id, segment.raw_sql,
                entity_id=entity_id,
                entity_type=EntityType.statement,
                confidence=0.85,
            )
            locations.append(loc)

    # ── 10. CASE WHEN 位置 ──────────────────────────────────────────────

    def _extract_case_when_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        ast,
        dialect: str,
    ) -> None:
        """定位每个 CASE WHEN 表达式的 range。"""
        if ast is None:
            return
        scope_id = "scope:root"
        ordinal = 0
        for case_node in ast.find_all(exp.Case):
            ordinal += 1
            entity_id = f"expression:{scope_id}:{ordinal}:case"
            case_sql = case_node.sql(dialect=dialect)
            loc = self._make_location(
                sql, sql_id, case_sql,
                entity_id=entity_id,
                entity_type=EntityType.expression,
                confidence=0.85,
            )
            locations.append(loc)

    # ── 11. 窗口函数位置 ────────────────────────────────────────────────

    def _extract_window_locations(
        self,
        locations: list[SourceLocation],
        sql: str,
        sql_id: str,
        ast,
        dialect: str,
    ) -> None:
        """定位每个 OVER (PARTITION BY ... ORDER BY ...) 的 range。"""
        if ast is None:
            return
        scope_id = "scope:root"
        ordinal = 0
        for win_node in ast.find_all(exp.Window):
            ordinal += 1
            entity_id = f"expression:{scope_id}:{ordinal}:window"
            win_sql = win_node.sql(dialect=dialect)
            loc = self._make_location(
                sql, sql_id, win_sql,
                entity_id=entity_id,
                entity_type=EntityType.expression,
                confidence=0.85,
            )
            locations.append(loc)


# ---------------------------------------------------------------------------
# 模块级辅助函数
# ---------------------------------------------------------------------------

def _build_resolved_column_lookup(
    resolved_columns: list[ResolvedColumnRef],
) -> dict[tuple[str | None, str], ResolvedColumnRef]:
    """构建 (table_alias_lower, column_lower) → ResolvedColumnRef 的查找表。"""
    lookup: dict[tuple[str | None, str], ResolvedColumnRef] = {}
    for resolved in resolved_columns:
        ref = resolved.reference
        table_key = ref.table.lower() if ref.table else None
        col_key = ref.column.lower()
        key = (table_key, col_key)
        if key not in lookup:
            lookup[key] = resolved
    return lookup


def _find_clause(ast, clause: str):
    """从 sqlglot AST 中查找指定子句节点。"""
    _clause_map = {
        "where": exp.Where,
        "group": exp.Group,
        "order": exp.Order,
    }
    exp_type = _clause_map.get(clause)
    if exp_type is None:
        return None
    return ast.find(exp_type)


def _unavailable_location(
    *,
    entity_id: str,
    entity_type: EntityType,
    sql_id: str,
    raw_text: str | None = None,
) -> SourceLocation:
    """创建 unavailable 类型的 SourceLocation。"""
    return SourceLocation(
        location_id=f"loc:unavailable:{hash_name(entity_id + ':' + (raw_text or ''))}",
        entity_id=entity_id,
        entity_type=entity_type,
        source_sql_id=sql_id,
        range_type="unavailable",
        raw_text=raw_text,
        confidence=0.0,
    )
