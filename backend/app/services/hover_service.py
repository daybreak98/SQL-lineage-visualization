"""SQL Hover 信息服务（M21）。

根据 SQL 文本和光标位置，返回光标处标识符的元数据信息。
"""

from __future__ import annotations

import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from app.domain.contracts import HoverInfo
from app.repositories.metadata_repository import MetadataRepository


def _cursor_offset(sql: str, line: int, col: int) -> int:
    """将 (line, col) 转为字符偏移量（0-based）。"""
    lines = sql.split("\n")
    offset = 0
    for i in range(min(line - 1, len(lines))):
        offset += len(lines[i]) + 1
    if line <= len(lines):
        offset += min(col - 1, len(lines[line - 1]))
    return offset


def _extract_identifier_at_offset(sql: str, offset: int) -> tuple[str | None, str | None]:
    """提取光标所在位置的 SQL 标识符名。

    返回 (word, prefix)：
    - word: 纯标识符名（不含表前缀）
    - prefix: 表前缀（如 "t" in "t.col"），无则为 None

    识别模式：
    - `table.column` → prefix="table", word="column"
    - `table` → word="table", prefix=None
    - `column` → word="column", prefix=None
    """
    if offset < 0 or offset > len(sql):
        return None, None

    # 标识符字符的正则
    ident_re = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

    # 从偏移量向左扫描，找到标识符开头
    start = offset
    while start > 0 and ident_re.match(sql[start - 1:start]):
        start -= 1

    # 从偏移量向右扫描，找到标识符结尾
    end = offset
    while end < len(sql) and ident_re.match(sql[end:end + 1]):
        end += 1

    word = sql[start:end] if start < end else None

    # 检查前面是否有 '.' 表示表前缀
    prefix = None
    if word and start > 0 and sql[start - 1] == ".":
        # 扫描点前的标识符
        dot_start = start - 2
        while dot_start >= 0 and ident_re.match(sql[dot_start:dot_start + 1]):
            dot_start -= 1
        dot_start += 1
        prefix = sql[dot_start:start - 1] if dot_start < start - 1 else None

    return word, prefix


def _find_table_alias_mapping(sql: str, dialect: str) -> dict[str, str]:
    """从 SQL 中提取表别名到表名的映射。

    Returns:
        {alias_lower: table_name}
    """
    mapping: dict[str, str] = {}
    try:
        ast = sqlglot.parse_one(sql, read=dialect)
        for table in ast.find_all(exp.Table):
            if table.alias and table.name:
                mapping[table.alias.lower()] = table.name
            if table.name:
                # 表名本身也作为映射
                mapping[table.name.lower()] = table.name
    except ParseError:
        pass
    return mapping


class HoverService:
    """SQL Hover 信息服务。"""

    def __init__(self, repo: MetadataRepository | None = None):
        self.repo = repo

    def get_hover(
        self,
        sql: str,
        cursor_line: int,
        cursor_col: int,
        dialect: str = "spark",
        metadata_version: str = "latest",
    ) -> HoverInfo | None:
        """返回光标处标识符的 hover 信息。"""
        if not sql.strip():
            return None

        offset = _cursor_offset(sql, cursor_line, cursor_col)
        word, prefix = _extract_identifier_at_offset(sql, offset)

        if not word:
            return None

        # 如果有前缀（如 t.col），word 是列名，prefix 是表别名
        if prefix:
            return self._hover_column_with_prefix(
                word, prefix, sql, dialect, metadata_version,
            )

        # 没有前缀：可能是表名，也可能是列名。先尝试表。
        table_result = self._hover_table(word, metadata_version)
        if table_result:
            return table_result

        # 再尝试列名（从 SQL 中已引用的表获取）
        column_result = self._hover_column(word, sql, dialect, metadata_version)
        if column_result:
            return column_result

        return None

    def _hover_table(
        self, name: str, metadata_version: str
    ) -> HoverInfo | None:
        """查询表名元数据。"""
        if not self.repo:
            return None

        try:
            table = self.repo.get_table_by_name(
                metadata_version=metadata_version,
                table_name=name,
            )
            if table:
                return HoverInfo(
                    text=table.get("table_name", ""),
                    type="table",
                    comment=table.get("comment"),
                    data_type="TABLE",
                    source=f"{table.get('catalog', 'default')}.{table.get('schema_name', 'default')}.{table.get('table_name', '')}",
                )
        except Exception:
            pass
        return None

    def _hover_column(
        self, name: str, sql: str, dialect: str, metadata_version: str
    ) -> HoverInfo | None:
        """查询列名元数据（从 SQL 中已引用的所有表搜索）。"""
        if not self.repo:
            return None

        alias_map = _find_table_alias_mapping(sql, dialect)

        try:
            # 遍历 SQL 中引用的所有表
            for alias, table_name in alias_map.items():
                table = self.repo.get_table_by_name(
                    metadata_version=metadata_version,
                    table_name=table_name,
                )
                if not table:
                    continue

                columns = self.repo.get_columns(
                    table_id=table["id"],
                    metadata_version=metadata_version,
                    limit=9999,
                )
                for col in columns:
                    if col.get("column_name", "").lower() == name.lower():
                        return HoverInfo(
                            text=col.get("column_name", ""),
                            type="column",
                            comment=col.get("comment"),
                            data_type=col.get("data_type", "unknown"),
                            source=f"{table.get('catalog', 'default')}.{table.get('schema_name', 'default')}.{table_name}.{col.get('column_name', '')}",
                        )
        except Exception:
            pass
        return None

    def _hover_column_with_prefix(
        self,
        col_name: str,
        prefix: str,
        sql: str,
        dialect: str,
        metadata_version: str,
    ) -> HoverInfo | None:
        """查询带表前缀的列名元数据。"""
        if not self.repo:
            return None

        alias_map = _find_table_alias_mapping(sql, dialect)
        table_name = alias_map.get(prefix.lower(), prefix)

        try:
            table = self.repo.get_table_by_name(
                metadata_version=metadata_version,
                table_name=table_name,
            )
            if not table:
                return None

            columns = self.repo.get_columns(
                table_id=table["id"],
                metadata_version=metadata_version,
                limit=9999,
            )
            for col in columns:
                if col.get("column_name", "").lower() == col_name.lower():
                    return HoverInfo(
                        text=f"{prefix}.{col.get('column_name', '')}",
                        type="column",
                        comment=col.get("comment"),
                        data_type=col.get("data_type", "unknown"),
                        source=f"{table.get('catalog', 'default')}.{table.get('schema_name', 'default')}.{table_name}.{col.get('column_name', '')}",
                    )
        except Exception:
            pass
        return None
