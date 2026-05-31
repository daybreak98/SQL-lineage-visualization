"""SQL 解析适配器（M08）—— 封装 sqlglot，不直接暴露 AST 给外部。"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.domain.contracts import ParseResult


class SqlglotAdapter:
    SUPPORTED_DIALECTS = {'spark', 'hive', 'mysql', 'starrocks', 'doris'}

    @staticmethod
    def parse(sql: str, dialect: str = 'spark') -> ParseResult:
        """解析 SQL，返回 ParseResult（成功时含 AST，失败时含错误信息）。"""
        try:
            if dialect not in SqlglotAdapter.SUPPORTED_DIALECTS:
                dialect = 'spark'
            ast = sqlglot.parse_one(sql, read=dialect)
            return ParseResult(
                success=True,
                ast=ast,
                dialect=dialect,
                normalized_sql=ast.sql(dialect=dialect),
            )
        except ParseError as e:
            return ParseResult(
                success=False,
                ast=None,
                dialect=dialect,
                error=str(e),
                error_code='PARSE_ERROR',
            )

    @staticmethod
    def format(sql: str, dialect: str = 'spark') -> str:
        """格式化 SQL。"""
        if dialect not in SqlglotAdapter.SUPPORTED_DIALECTS:
            dialect = 'spark'
        return sqlglot.transpile(sql, read=dialect, pretty=True)[0]

    @staticmethod
    def get_table_names(sql: str, dialect: str = 'spark') -> list[str]:
        """提取 SQL 中引用的表名。"""
        try:
            ast = sqlglot.parse_one(sql, read=dialect)
            tables = []
            for table in ast.find_all(exp.Table):
                name = table.name
                if table.catalog:
                    name = f"{table.catalog}.{name}"
                if table.db:
                    name = f"{table.db}.{name}"
                tables.append(name)
            return list(set(tables))
        except ParseError:
            return []

    @staticmethod
    def get_column_names(sql: str, dialect: str = 'spark') -> list[str]:
        """提取 SQL 中引用的字段名（select 子句中的）。"""
        try:
            ast = sqlglot.parse_one(sql, read=dialect)
            columns = []
            for col in ast.find_all(exp.Column):
                name = col.name
                if col.table:
                    name = f"{col.table}.{name}"
                columns.append(name)
            return list(set(columns))
        except ParseError:
            return []
