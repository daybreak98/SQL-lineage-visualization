"""P0 ScopeResolver: FROM/JOIN relations and SELECT outputs."""

from __future__ import annotations

from sqlglot import exp

from app.diagnostics.collector import DiagnosticsCollector
from app.domain.contracts import Diagnostic, DiagnosticCode, DiagnosticLevel
from app.domain.entity_id import EntityIdFactory
from app.domain.scope_model import ColumnReference, ScopeModel, ScopeRelation, ScopeSelectItem


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

        seen_aliases: set[str] = set()
        for table in self._tables_in_root_scope(ast):
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
            model.relations.append(
                ScopeRelation(
                    relation_id=EntityIdFactory.scope_relation(scope_id, alias),
                    scope_id=scope_id,
                    alias=alias,
                    catalog=catalog,
                    schema=schema,
                    table=table.name,
                    table_entity_id=entity_id,
                    source_name=table.sql(dialect=parse_result.dialect),
                )
            )

        expressions = getattr(ast, "expressions", []) or []
        for ordinal, expression in enumerate(expressions, start=1):
            model.select_items.append(
                ScopeSelectItem(
                    select_id=f"select:{scope_id}:{ordinal}",
                    scope_id=scope_id,
                    ordinal=ordinal,
                    expression_sql=expression.sql(dialect=parse_result.dialect),
                    output_name=self._output_name(expression, ordinal),
                    alias=expression.alias or None,
                    expression_kind=self._expression_kind(expression),
                    source_columns=self._column_refs(expression, parse_result.dialect),
                )
            )

        return model, collector.list()

    @staticmethod
    def _tables_in_root_scope(ast) -> list[exp.Table]:
        tables: list[exp.Table] = []
        from_expr = ast.args.get("from") or ast.args.get("from_")
        if from_expr is not None and isinstance(from_expr.this, exp.Table):
            tables.append(from_expr.this)
        for join in ast.args.get("joins") or []:
            if isinstance(join.this, exp.Table):
                tables.append(join.this)
        return tables

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
