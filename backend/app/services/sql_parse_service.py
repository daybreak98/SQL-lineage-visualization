"""SQL 解析服务层（R03 / M08）。"""

from app.adapters.sqlglot_adapter import SqlglotAdapter
from app.domain.contracts import Diagnostic, DiagnosticCode, DiagnosticLevel


class SqlParseService:
    def __init__(self):
        self.adapter = SqlglotAdapter()

    def parse(self, sql: str, dialect: str = 'spark'):
        """解析 SQL，返回 (ParseResult, list[Diagnostic])。"""
        result = self.adapter.parse(sql, dialect)
        diagnostics = []
        if not result.success:
            diagnostics.append(Diagnostic(
                diagnostic_id="diag:PARSE_ERROR:1",
                code=DiagnosticCode.PARSE_ERROR,
                level=DiagnosticLevel.error,
                message=result.error or "SQL 解析失败",
                suggestion="请检查 SQL 语法",
                source_location_id=None,
                related_entity_ids=[],
                details={"dialect": dialect},
            ))
        return result, diagnostics

    def format(self, sql: str, dialect: str = 'spark'):
        """格式化 SQL。"""
        try:
            formatted = self.adapter.format(sql, dialect)
            return formatted, []
        except Exception as e:
            return None, [Diagnostic(
                diagnostic_id="diag:PARSE_ERROR:1",
                code=DiagnosticCode.PARSE_ERROR,
                level=DiagnosticLevel.error,
                message=str(e),
                suggestion="请检查 SQL 语法",
            )]

    def extract_tables(self, sql: str, dialect: str = 'spark') -> list[str]:
        return self.adapter.get_table_names(sql, dialect)

    def extract_columns(self, sql: str, dialect: str = 'spark') -> list[str]:
        return self.adapter.get_column_names(sql, dialect)
