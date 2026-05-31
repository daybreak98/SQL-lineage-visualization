"""SQL 自动补全服务（M21）。

根据 SQL 文本和光标位置，返回补全候选（表名、字段名、关键字）。
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.domain.contracts import CompletionCandidate
from app.repositories.metadata_repository import MetadataRepository


# 常用 SQL 关键字
_SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
    "FULL", "CROSS", "ON", "AND", "OR", "NOT", "IN", "EXISTS", "BETWEEN",
    "LIKE", "IS", "NULL", "AS", "DISTINCT", "ALL", "UNION", "INTERSECT",
    "EXCEPT", "ORDER", "BY", "ASC", "DESC", "GROUP", "HAVING", "LIMIT",
    "OFFSET", "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
    "CREATE", "TABLE", "VIEW", "ALTER", "DROP", "WITH", "CASE", "WHEN",
    "THEN", "ELSE", "END", "CAST", "COUNT", "SUM", "AVG", "MIN", "MAX",
    "COALESCE", "IFNULL", "NVL", "NULLIF", "TRUE", "FALSE",
]

# 常用 SQL 函数
_SQL_FUNCTIONS = [
    "COUNT", "SUM", "AVG", "MIN", "MAX", "COALESCE", "IFNULL", "NVL",
    "NULLIF", "CAST", "CONCAT", "SUBSTR", "TRIM", "UPPER", "LOWER",
    "LENGTH", "REPLACE", "ROUND", "FLOOR", "CEIL", "ABS", "DATE",
    "DATE_FORMAT", "NOW", "CURRENT_DATE", "CURRENT_TIMESTAMP",
    "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD", "FIRST_VALUE",
    "LAST_VALUE", "SUM", "COUNT", "AVG", "MIN", "MAX",
]


def _cursor_offset(sql: str, line: int, col: int) -> int:
    """将 (line, col) 转为字符偏移量（0-based）。"""
    lines = sql.split("\n")
    offset = 0
    for i in range(min(line - 1, len(lines))):
        offset += len(lines[i]) + 1  # +1 for newline
    offset += min(col - 1, len(lines[line - 1]) if line <= len(lines) else 0)
    return min(offset, len(sql))


def _find_context(sql: str, offset: int, dialect: str) -> str:
    """推断光标所在 SQL 上下文。

    Returns:
        "table" — 光标在 FROM/JOIN 后，应补全表名
        "column" — 光标在 SELECT/WHERE 后，应补全字段名
        "keyword" — 默认补全关键字
    """
    if not sql.strip():
        return "keyword"

    prefix = sql[:offset].strip()
    if not prefix:
        return "keyword"

    # 简单启发式：看最后一个有效 token 之前的上下文
    upper_prefix = prefix.upper().split()
    if not upper_prefix:
        return "keyword"

    # 检查最后一个非单词结尾是否是 FROM / JOIN
    # 更精确地：找 FROM 或 JOIN 后面但不在子查询或 ON 后的位置
    from_count = 0
    join_count = 0

    # 用 sqlglot tokenizer 来分析上下文
    try:
        tokens = list(sqlglot.tokenize(prefix, dialect=dialect))
    except Exception:
        tokens = []

    # 查找最近的结构性 token（按 token 文本匹配）
    last_struct = None
    for tok in tokens:
        kw = tok.text.upper()
        if kw.isalpha() and len(kw) >= 2:
            if kw in ("FROM", "JOIN", "INNER", "LEFT", "RIGHT", "CROSS", "FULL"):
                last_struct = "from_or_join"
            elif kw in ("SELECT",):
                last_struct = "select"
            elif kw in ("WHERE", "AND", "OR", "HAVING"):
                last_struct = "where"
            elif kw in ("ON",):
                last_struct = "on"
            elif kw in ("GROUP", "ORDER", "BY"):
                last_struct = "column"
            elif kw == "SET":
                last_struct = "set"
            elif kw == "INTO":
                last_struct = "into"
            elif kw == "TABLE":
                last_struct = "table"

    # 如果没有找到任何上下文 token，用启发式回退
    if last_struct is None:
        if "FROM" in upper_prefix or "JOIN" in upper_prefix:
            last_struct = "from_or_join"
        elif "SELECT" in upper_prefix and "FROM" not in upper_prefix:
            return "column"
        else:
            return "keyword"

    # FROM/JOIN 后 → 补全表名
    if last_struct in ("from_or_join", "into"):
        paren_depth = prefix.count("(") - prefix.count(")")
        if paren_depth <= 0:
            return "table"

    return "column"


def _get_tables_from_sql(sql: str, dialect: str) -> list[str]:
    """提取 SQL 中已引用的表名（含别名）。"""
    try:
        ast = sqlglot.parse_one(sql, read=dialect)
    except ParseError:
        return []
    tables = []
    for table in ast.find_all(exp.Table):
        if table.alias:
            tables.append(table.alias)
        if table.name:
            tables.append(table.name)
    return list(set(tables))


class CompletionService:
    """SQL 自动补全服务。"""

    def __init__(self, repo: MetadataRepository | None = None):
        self.repo = repo

    def get_completions(
        self,
        sql: str,
        cursor_line: int,
        cursor_col: int,
        dialect: str = "spark",
        metadata_version: str = "latest",
    ) -> list[CompletionCandidate]:
        """根据 SQL 和光标位置返回补全候选。"""
        offset = _cursor_offset(sql, cursor_line, cursor_col)
        context = _find_context(sql, offset, dialect)

        candidates: list[CompletionCandidate] = []

        if context == "table":
            candidates = self._table_completions(metadata_version)
        elif context == "column":
            candidates = self._column_completions(sql, dialect, metadata_version)
        else:
            candidates = self._keyword_completions()

        # 总是追加关键字补全
        if context != "keyword":
            candidates.extend(self._keyword_completions())

        return candidates

    def _table_completions(self, metadata_version: str) -> list[CompletionCandidate]:
        """从元数据获取表名补全候选。"""
        candidates: list[CompletionCandidate] = []

        if self.repo:
            try:
                tables = self.repo.get_tables(
                    metadata_version=metadata_version,
                    limit=100,
                )
                for t in tables:
                    candidates.append(CompletionCandidate(
                        text=t.get("table_name", ""),
                        type="table",
                        detail=f"{t.get('catalog', 'default')}.{t.get('schema_name', 'default')}.{t.get('table_name', '')}",
                    ))
            except Exception:
                pass

        return candidates

    def _column_completions(
        self,
        sql: str,
        dialect: str,
        metadata_version: str,
    ) -> list[CompletionCandidate]:
        """从元数据获取字段名补全候选。

        优先从 SQL 中已引用的表获取字段列表。
        """
        candidates: list[CompletionCandidate] = []

        if self.repo:
            # 尝试从 SQL 中提取表名
            table_names = _get_tables_from_sql(sql, dialect)

            for tname in table_names:
                try:
                    table = self.repo.get_table_by_name(
                        metadata_version=metadata_version,
                        table_name=tname,
                    )
                    if table:
                        columns = self.repo.get_columns(
                            table_id=table["id"],
                            metadata_version=metadata_version,
                            limit=9999,
                        )
                        for col in columns:
                            detail_parts = [col.get("data_type", "unknown")]
                            if col.get("comment"):
                                detail_parts.append(col.get("comment", ""))
                            candidates.append(CompletionCandidate(
                                text=col.get("column_name", ""),
                                type="column",
                                detail=" | ".join(detail_parts),
                            ))
                except Exception:
                    continue

            # 如果没有表名上下文，返回所有已导入表的字段
            if not candidates:
                try:
                    tables = self.repo.get_tables(
                        metadata_version=metadata_version,
                        limit=50,
                    )
                    for t in tables:
                        columns = self.repo.get_columns(
                            table_id=t["id"],
                            metadata_version=metadata_version,
                            limit=200,
                        )
                        for col in columns:
                            candidates.append(CompletionCandidate(
                                text=f"{t.get('table_name', '')}.{col.get('column_name', '')}",
                                type="column",
                                detail=col.get("data_type", "unknown"),
                            ))
                except Exception:
                    pass

        return candidates

    @staticmethod
    def _keyword_completions() -> list[CompletionCandidate]:
        """返回 SQL 关键字和函数补全候选。"""
        candidates: list[CompletionCandidate] = []
        for kw in _SQL_KEYWORDS:
            candidates.append(CompletionCandidate(
                text=kw,
                type="keyword",
                detail=None,
            ))
        for func in set(_SQL_FUNCTIONS):
            candidates.append(CompletionCandidate(
                text=func,
                type="function",
                detail=None,
            ))
        return candidates
