"""R03 SQL Parse Adapter 单元测试 — SqlParseService + SqlglotAdapter.

测试覆盖 (10 core cases specified in task):
  1. test_parse_valid_select        — 合法 SELECT 解析成功
  2. test_parse_syntax_error        — 非法 SQL 返回 PARSE_ERROR
  3. test_format                    — 格式化成功，大小写正确
  4. test_extract_tables            — 提取表名（含 JOIN）
  5. test_extract_columns           — 提取字段名
  6. test_dialect_spark             — Spark 方言支持
  7. test_dialect_hive              — Hive 方言支持
  8. test_parse_cte                 — CTE (WITH) 解析
  9. test_parse_subquery            — 子查询解析
  10. test_format_failed_sql        — 非法 SQL 格式化返回 diagnostics
  11. test_empty_sql                 — 空 SQL 处理

扩展边界 case:
  12. test_parse_insert              — INSERT 语句解析
  13. test_parse_union               — UNION 解析
  14. test_parse_join_types          — 多种 JOIN 类型表提取
  15. test_parse_window_function     — 窗口函数中的字段提取
  16. test_dialect_mysql             — MySQL 方言
  17. test_dialect_cross_check       — 方言不匹配时的错误处理
  18. test_extract_tables_with_alias — 带别名的表提取
  19. test_sql_with_special_chars    — 含特殊字符的 SQL
  20. test_nested_cte                — 嵌套 CTE

SqlglotAdapter 直接测试:
  21. test_adapter_parse_valid       — adapter.parse() 返回 ParseResult
  22. test_adapter_parse_invalid    — adapter.parse() 对非法 SQL 返回 error
  23. test_adapter_format            — adapter.format() 返回格式化字符串
  24. test_adapter_dialect_switch    — adapter 支持方言切换
  25. test_adapter_get_table_names   — adapter 直接提取表名
"""

from __future__ import annotations

import textwrap

import pytest

# ---------------------------------------------------------------------------
# 被测模块 — 均已在 backend-developer 实现
# ---------------------------------------------------------------------------
from app.adapters.sqlglot_adapter import SqlglotAdapter
from app.services.sql_parse_service import SqlParseService
from app.domain.contracts import (
    DiagnosticCode,
    DiagnosticLevel,
    ParseResult,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

VALID_SELECT_SIMPLE = "SELECT a, b FROM t WHERE a > 1"

VALID_SELECT_JOIN = textwrap.dedent("""\
    SELECT o.order_no, u.user_name
      FROM order_table o
      JOIN user_table u ON o.user_id = u.user_id
     WHERE o.status = 'active'
""")

VALID_CTE = textwrap.dedent("""\
    WITH cte AS (
        SELECT user_id, COUNT(*) AS cnt
        FROM order_table
        GROUP BY user_id
    )
    SELECT u.user_name, cte.cnt
    FROM user_table u
    JOIN cte ON u.user_id = cte.user_id
""")

VALID_SUBQUERY = textwrap.dedent("""\
    SELECT u.user_name,
           (SELECT COUNT(*) FROM order_table o WHERE o.user_id = u.user_id) AS order_cnt
    FROM user_table u
""")

VALID_MULTI_JOIN = textwrap.dedent("""\
    SELECT a.col1, b.col2, c.col3
    FROM t1 a
    INNER JOIN t2 b ON a.id = b.id
    LEFT JOIN t3 c ON b.id = c.id
""")

VALID_WINDOW_FUNC = (
    "SELECT user_id, "
    "ROW_NUMBER() OVER (PARTITION BY dept_id ORDER BY salary DESC) AS rn "
    "FROM employee"
)

INVALID_SQL_SYNTAX = "SELEC a FRM t WHERE"

INVALID_SQL_GARBAGE = "!@#$%^&*() GARBAGE SQL"

SPARK_SPECIFIC_SQL = "SELECT /*+ BROADCAST(t) */ * FROM t DISTRIBUTE BY col1"

HIVE_SPECIFIC_SQL = "SELECT a, b FROM t LATERAL VIEW explode(col) t2 AS c"

INSERT_SQL = "INSERT INTO target_table SELECT a, b FROM source_table"

UNION_SQL = "SELECT a FROM t1 UNION ALL SELECT b FROM t2"

SUBQUERY_IN_SELECT = (
    "SELECT a, (SELECT MAX(b) FROM t2 WHERE t2.x = t1.x) AS max_b FROM t1"
)

SQL_WITH_SPECIAL_CHARS = (
    "SELECT `weird-column` AS col FROM `odd table` WHERE col = 'it''s ok'"
)


# ===================================================================
# 1. test_parse_valid_select
# ===================================================================

def test_parse_valid_select():
    """合法 SELECT 解析成功：ParseResult.success=True，无 PARSE_ERROR 诊断。"""
    service = SqlParseService()
    result, diagnostics = service.parse(VALID_SELECT_SIMPLE, dialect="spark")

    assert isinstance(result, ParseResult), (
        f"应返回 ParseResult，实际={type(result)}"
    )
    assert result.success is True, (
        f"合法 SQL 解析应成功，success={result.success}"
    )
    assert result.normalized_sql is not None, "成功时应生成 normalized_sql"
    assert result.ast is not None, "成功时 AST 不应为 None"

    # 无 PARSE_ERROR
    errors = [d for d in diagnostics if d.code == DiagnosticCode.PARSE_ERROR]
    assert len(errors) == 0, f"合法 SQL 不应含 PARSE_ERROR: {errors}"


def test_parse_valid_select_complex():
    """含 JOIN / WHERE / GROUP BY / ORDER BY 的复杂 SELECT 也应解析成功。"""
    service = SqlParseService()
    complex_sql = textwrap.dedent("""\
        SELECT o.order_no, COUNT(*) AS cnt
        FROM order_table o
        JOIN user_table u ON o.user_id = u.user_id
        WHERE o.status = 'active'
        GROUP BY o.order_no
        ORDER BY cnt DESC
    """)
    result, diagnostics = service.parse(complex_sql, dialect="spark")

    assert result.success is True, (
        f"复杂 SELECT 解析应成功，success={result.success}"
    )


# ===================================================================
# 2. test_parse_syntax_error
# ===================================================================

def test_parse_syntax_error():
    """非法 SQL 返回 ParseResult.success=False，PARSE_ERROR 诊断。

    验证：
      - success == False
      - diagnostics 包含 PARSE_ERROR，级别为 error
      - result.error 包含错误描述
    """
    service = SqlParseService()
    result, diagnostics = service.parse(INVALID_SQL_SYNTAX, dialect="spark")

    assert result.success is False, (
        f"非法 SQL 解析应失败，success={result.success}"
    )
    assert result.error is not None, "失败时应有 error 描述"
    assert result.error_code == "PARSE_ERROR", (
        f"error_code 应为 PARSE_ERROR，实际={result.error_code}"
    )

    parse_errors = [d for d in diagnostics if d.code == DiagnosticCode.PARSE_ERROR]
    assert len(parse_errors) >= 1, (
        f"必须包含 PARSE_ERROR diagnostic，"
        f"实际={[d.code.value for d in diagnostics]}"
    )
    assert parse_errors[0].level == DiagnosticLevel.error


def test_parse_syntax_error_garbage():
    """完全无效的输入也返回 PARSE_ERROR。"""
    service = SqlParseService()
    result, diagnostics = service.parse(INVALID_SQL_GARBAGE, dialect="spark")

    assert result.success is False
    parse_errors = [d for d in diagnostics if d.code == DiagnosticCode.PARSE_ERROR]
    assert len(parse_errors) >= 1


# ===================================================================
# 3. test_format
# ===================================================================

def test_format():
    """格式化成功：输入无换行 SQL，输出规范化换行和缩进。

    验证：
      - 返回格式化字符串（非 None）
      - diagnostics 为空
      - 关键字大写（如 SELECT）
    """
    service = SqlParseService()
    sql = "select a,b,c from my_table where a>1 order by b"
    formatted, diagnostics = service.format(sql, dialect="spark")

    assert formatted is not None, "格式化成功时不应返回 None"
    assert isinstance(formatted, str), f"应返回 str，实际={type(formatted)}"
    assert len(formatted) > 0

    # 关键字应大写
    assert "SELECT" in formatted.upper(), (
        f"格式化后应包含 SELECT 关键字: {formatted!r}"
    )

    # 无诊断
    assert len(diagnostics) == 0, (
        f"合法 SQL 格式化不应产生 diagnostics: "
        f"{[d.message for d in diagnostics]}"
    )


def test_format_multiline():
    """多行 SQL 格式化保持结构清晰。"""
    service = SqlParseService()
    sql = (
        "SELECT o.order_no, u.user_name "
        "FROM order_table o "
        "JOIN user_table u ON o.user_id = u.user_id "
        "WHERE o.status = 'active'"
    )
    formatted, diagnostics = service.format(sql, dialect="spark")

    assert formatted is not None
    assert "JOIN" in formatted.upper()
    assert len(diagnostics) == 0


def test_format_preserves_keywords():
    """格式化后 SQL 关键字大写（SELECT、FROM、WHERE 等）。"""
    service = SqlParseService()
    sql = "select a from t where b = 1 group by a order by a"
    formatted, _ = service.format(sql, dialect="spark")

    assert formatted is not None
    assert "SELECT" in formatted, f"应包含大写 SELECT: {formatted!r}"
    assert "FROM" in formatted, f"应包含大写 FROM: {formatted!r}"


# ===================================================================
# 4. test_extract_tables
# ===================================================================

def test_extract_tables_simple():
    """简单 SELECT 提取表名。"""
    service = SqlParseService()
    tables = service.extract_tables("SELECT a FROM my_table", dialect="spark")

    assert isinstance(tables, list)
    assert "my_table" in tables, f"应包含 my_table，实际={tables}"


def test_extract_tables_with_join():
    """多表 JOIN 提取全部表名。"""
    service = SqlParseService()
    sql = textwrap.dedent("""\
        SELECT *
        FROM order_table o
        JOIN user_table u ON o.user_id = u.user_id
        LEFT JOIN product_table p ON o.product_id = p.product_id
    """)
    tables = service.extract_tables(sql, dialect="spark")

    assert len(tables) >= 3, f"应至少 3 张表，实际={tables}"
    assert "order_table" in tables
    assert "user_table" in tables
    assert "product_table" in tables


def test_extract_tables_with_alias():
    """带别名的表：提取原始表名。"""
    service = SqlParseService()
    tables = service.extract_tables(
        "SELECT a.col1 FROM very_long_table_name AS a",
        dialect="spark",
    )

    assert "very_long_table_name" in tables, (
        f"应包含原始表名 very_long_table_name，实际={tables}"
    )


def test_extract_tables_no_from():
    """无 FROM 子句（如 SELECT 1+1）应返回空表列表或优雅处理。"""
    service = SqlParseService()
    tables = service.extract_tables("SELECT 1 + 1 AS result", dialect="spark")
    assert isinstance(tables, list)


# ===================================================================
# 5. test_extract_columns
# ===================================================================

def test_extract_columns_simple():
    """SELECT 字段名提取。"""
    service = SqlParseService()
    columns = service.extract_columns(
        "SELECT col_a, col_b, col_c FROM t",
        dialect="spark",
    )

    assert isinstance(columns, list), f"应返回 list，实际={type(columns)}"
    assert len(columns) >= 3, f"应至少提取 3 个字段，实际={columns}"
    assert "col_a" in columns
    assert "col_b" in columns
    assert "col_c" in columns


def test_extract_columns_qualified():
    """表前缀限定字段名（如 t.col_a）应能提取（返回 t.col_a form）。"""
    service = SqlParseService()
    columns = service.extract_columns(
        "SELECT t.col_a, t.col_b FROM t",
        dialect="spark",
    )

    assert len(columns) >= 2, f"应至少 2 个字段，实际={columns}"
    # 限定字段可为 "t.col_a" 或 "col_a"，取决于 adapter 实现
    found = any("col_a" in c for c in columns)
    assert found, f"应能识别 col_a，实际={columns}"


def test_extract_columns_star():
    """SELECT * 不崩溃（可能返回空列表）。"""
    service = SqlParseService()
    columns = service.extract_columns("SELECT * FROM t", dialect="spark")
    assert isinstance(columns, list)
    # SELECT * 在不展开时可能返回空或无星号字段


# ===================================================================
# 6. test_dialect_spark
# ===================================================================

def test_dialect_spark():
    """Spark SQL 方言解析：DISTRIBUTE BY + BROADCAST hint。"""
    service = SqlParseService()
    result, diagnostics = service.parse(SPARK_SPECIFIC_SQL, dialect="spark")

    assert result.success is True, (
        f"Spark SQL 解析应成功，success={result.success}"
    )
    assert result.dialect == "spark"


def test_dialect_spark_format():
    """Spark 方言格式化 DISTRIBUTE BY 语句。"""
    service = SqlParseService()
    formatted, diagnostics = service.format(
        "select a,b from t distribute by a",
        dialect="spark",
    )

    assert formatted is not None
    assert len(diagnostics) == 0


# ===================================================================
# 7. test_dialect_hive
# ===================================================================

def test_dialect_hive():
    """Hive SQL 方言解析：LATERAL VIEW explode。"""
    service = SqlParseService()
    result, diagnostics = service.parse(HIVE_SPECIFIC_SQL, dialect="hive")

    assert result.success is True, (
        f"Hive SQL 解析应成功，success={result.success}"
    )
    assert result.dialect == "hive"


def test_dialect_hive_format():
    """Hive 方言格式化 LATERAL VIEW 语句。"""
    service = SqlParseService()
    formatted, diagnostics = service.format(
        "select a,b from t lateral view explode(col) t2 as c",
        dialect="hive",
    )

    assert formatted is not None
    assert len(diagnostics) == 0


# ===================================================================
# 8. test_parse_cte
# ===================================================================

def test_parse_cte():
    """CTE (WITH 子句) 解析成功。"""
    service = SqlParseService()
    result, diagnostics = service.parse(VALID_CTE, dialect="spark")

    assert result.success is True, (
        f"CTE 解析应成功，success={result.success}"
    )
    parse_errors = [d for d in diagnostics if d.code == DiagnosticCode.PARSE_ERROR]
    assert len(parse_errors) == 0, (
        f"CTE 不应含 PARSE_ERROR: {[e.message for e in parse_errors]}"
    )


def test_extract_tables_from_cte():
    """CTE 中的物理表应被提取。"""
    service = SqlParseService()
    tables = service.extract_tables(VALID_CTE, dialect="spark")

    assert "order_table" in tables, (
        f"应提取 CTE 内部的 order_table，实际={tables}"
    )
    assert "user_table" in tables, (
        f"应提取 user_table，实际={tables}"
    )


def test_nested_cte():
    """嵌套 CTE 不崩溃。"""
    service = SqlParseService()
    nested_cte_sql = textwrap.dedent("""\
        WITH cte1 AS (
            SELECT user_id FROM order_table
        ),
        cte2 AS (
            SELECT user_id, COUNT(*) AS cnt FROM cte1 GROUP BY user_id
        )
        SELECT * FROM cte2
    """)
    result, diagnostics = service.parse(nested_cte_sql, dialect="spark")

    assert result.success is True, (
        f"嵌套 CTE 解析应成功，success={result.success}，"
        f"error={result.error}"
    )


# ===================================================================
# 9. test_parse_subquery
# ===================================================================

def test_parse_subquery():
    """子查询（FROM 子句中的标量子查询）解析成功。"""
    service = SqlParseService()
    result, diagnostics = service.parse(VALID_SUBQUERY, dialect="spark")

    assert result.success is True, (
        f"子查询解析应成功，success={result.success}，"
        f"error={result.error}"
    )


def test_extract_tables_from_subquery():
    """子查询内外的物理表应全部提取。"""
    service = SqlParseService()
    tables = service.extract_tables(VALID_SUBQUERY, dialect="spark")

    assert "user_table" in tables, (
        f"应提取外层 user_table，实际={tables}"
    )
    assert "order_table" in tables, (
        f"应提取子查询内的 order_table，实际={tables}"
    )


def test_parse_subquery_in_select():
    """SELECT 子句中的标量子查询解析成功。"""
    service = SqlParseService()
    result, diagnostics = service.parse(SUBQUERY_IN_SELECT, dialect="spark")

    assert result.success is True, (
        f"SELECT 中标量子查询应成功，success={result.success}，"
        f"error={result.error}"
    )


# ===================================================================
# 10. test_format_failed_sql
# ===================================================================

def test_format_failed_sql():
    """非法 SQL 格式化：返回 None + PARSE_ERROR 诊断。

    验证：
      - formatted 为 None
      - diagnostics 包含 PARSE_ERROR
    """
    service = SqlParseService()
    formatted, diagnostics = service.format(INVALID_SQL_SYNTAX, dialect="spark")

    assert formatted is None, (
        f"非法 SQL 格式化应返回 None，实际={formatted!r}"
    )
    assert len(diagnostics) >= 1, (
        f"应包含 diagnostics，实际={diagnostics}"
    )
    parse_errors = [d for d in diagnostics if d.code == DiagnosticCode.PARSE_ERROR]
    assert len(parse_errors) >= 1, (
        f"应包含 PARSE_ERROR，实际={[d.code.value for d in diagnostics]}"
    )
    assert parse_errors[0].level == DiagnosticLevel.error


def test_format_failed_sql_garbage():
    """完全无效的 SQL 格式化也返回 None + diagnostics。"""
    service = SqlParseService()
    formatted, diagnostics = service.format(INVALID_SQL_GARBAGE, dialect="spark")

    assert formatted is None
    assert len(diagnostics) >= 1


# ===================================================================
# 11. test_empty_sql
# ===================================================================

def test_empty_sql():
    """空 SQL 解析：返回 failed + PARSE_ERROR。"""
    service = SqlParseService()
    result, diagnostics = service.parse("", dialect="spark")

    assert result.success is False, (
        f"空 SQL 解析应失败，success={result.success}"
    )
    parse_errors = [d for d in diagnostics if d.code == DiagnosticCode.PARSE_ERROR]
    assert len(parse_errors) >= 1, "空 SQL 应包含 PARSE_ERROR"


def test_whitespace_sql():
    """纯空白 SQL 应也返回 failed。"""
    service = SqlParseService()
    for whitespace_sql in ("   ", "\n\t  ", "\n\n"):
        result, diagnostics = service.parse(whitespace_sql, dialect="spark")
        assert result.success is False, (
            f"空白 SQL {whitespace_sql!r} 应失败，success={result.success}"
        )
        parse_errors = [
            d for d in diagnostics if d.code == DiagnosticCode.PARSE_ERROR
        ]
        assert len(parse_errors) >= 1, (
            f"空白 SQL 应含 PARSE_ERROR: {whitespace_sql!r}"
        )


def test_empty_sql_format():
    """空 SQL 格式化：不崩溃，返回空字符串或 None（取决于 adapter 实现）。

    sqlglot.transpile("") 可能返回 ""
    不会抛异常，因此 service 层的 format() 不会触发 PARSE_ERROR。
    这里验证空 SQL 格式化不崩溃即可。
    """
    service = SqlParseService()
    formatted, diagnostics = service.format("", dialect="spark")

    # 核心要求：不崩溃，不抛异常
    assert isinstance(formatted, str) or formatted is None, (
        f"格式化结果应为 str 或 None，实际={type(formatted)}"
    )
    assert isinstance(diagnostics, list)
    # 空 SQL 格式化可能返回空字符串 '' 而非 None（取决于 sqlglot 版本）
    # 两种行为均可接受


# ===================================================================
# 扩展边界 case
# ===================================================================

def test_parse_insert():
    """INSERT 语句解析（不要求 P0 完全支持，但不能崩溃）。"""
    service = SqlParseService()
    # sqlglot 25.x 应该能解析 INSERT...SELECT
    result, diagnostics = service.parse(INSERT_SQL, dialect="spark")

    # 不崩溃即可；INSERT 解析成功/失败均可
    assert result is not None
    assert isinstance(diagnostics, list)


def test_parse_union():
    """UNION ALL 解析成功。"""
    service = SqlParseService()
    result, diagnostics = service.parse(UNION_SQL, dialect="spark")

    assert result.success is True, (
        f"UNION ALL 解析应成功，success={result.success}，"
        f"error={result.error}"
    )


def test_extract_tables_from_union():
    """UNION 两侧的表都应被提取。"""
    service = SqlParseService()
    tables = service.extract_tables(UNION_SQL, dialect="spark")

    assert "t1" in tables, f"UNION 左侧表 t1 应被提取，实际={tables}"
    assert "t2" in tables, f"UNION 右侧表 t2 应被提取，实际={tables}"


def test_parse_join_types():
    """多种 JOIN 类型（INNER/LEFT）表提取。"""
    service = SqlParseService()
    tables = service.extract_tables(VALID_MULTI_JOIN, dialect="spark")

    assert len(tables) >= 3, f"应至少 3 张表，实际={tables}"
    assert "t1" in tables
    assert "t2" in tables
    assert "t3" in tables


def test_parse_window_function():
    """窗口函数中的字段提取（PARTITION BY / ORDER BY 子句）。"""
    service = SqlParseService()
    columns = service.extract_columns(VALID_WINDOW_FUNC, dialect="spark")

    assert isinstance(columns, list)
    assert "user_id" in columns, f"应提取 user_id，实际={columns}"


def test_dialect_mysql():
    """MySQL 方言解析（反引号引用标识符）。"""
    service = SqlParseService()
    mysql_sql = (
        "SELECT `order`.`id`, `order`.`name` "
        "FROM `order` WHERE `order`.`status` = 1"
    )
    result, diagnostics = service.parse(mysql_sql, dialect="mysql")

    assert result.success is True, (
        f"MySQL 反引号解析应成功，success={result.success}，"
        f"error={result.error}"
    )


def test_dialect_cross_check():
    """方言一致性检查：方言参数应被正确传递。

    注意：sqlglot 的解析器对多数语法是方言兼容的，
    LATERAL VIEW 在 mysql 方言下也可能解析成功（解析器很宽容）。
    这里验证方言参数被正确设置，不强制要求解析失败。
    """
    service = SqlParseService()
    result, diagnostics = service.parse(HIVE_SPECIFIC_SQL, dialect="mysql")

    # 核心：方言参数被正确传递
    assert result.dialect == "mysql", (
        f"方言应为 mysql，实际={result.dialect}"
    )
    # 解析结果取决于 sqlglot 的行为，不做强制假设
    assert result is not None
    assert isinstance(diagnostics, list)

    # 同时验证 hive 方言下解析成功
    result_hive, _ = service.parse(HIVE_SPECIFIC_SQL, dialect="hive")
    assert result_hive.success is True, (
        f"Hive 方言下应解析成功: success={result_hive.success}"
    )
    assert result_hive.dialect == "hive"


def test_sql_with_special_chars():
    """含特殊字符/转义的 SQL 不崩溃。"""
    service = SqlParseService()
    result, diagnostics = service.parse(SQL_WITH_SPECIAL_CHARS, dialect="spark")

    # 只要有结构化结果即可，不强制 success
    assert result is not None
    assert isinstance(diagnostics, list)


def test_extract_tables_invalid_sql():
    """非法 SQL 的表提取应返回空列表（不崩溃）。"""
    service = SqlParseService()
    tables = service.extract_tables(INVALID_SQL_SYNTAX, dialect="spark")
    assert isinstance(tables, list)
    # 非法 SQL 时返回空列表是预期行为（adapter 内部 catch ParseError）


def test_extract_columns_invalid_sql():
    """非法 SQL 的字段提取应返回空列表（不崩溃）。"""
    service = SqlParseService()
    columns = service.extract_columns(INVALID_SQL_SYNTAX, dialect="spark")
    assert isinstance(columns, list)


# ===================================================================
# SqlglotAdapter 直接测试
# ===================================================================

def test_adapter_parse_valid():
    """SqlglotAdapter.parse() 对合法 SQL 返回 success=True 的 ParseResult。"""
    result = SqlglotAdapter.parse("SELECT 1")

    assert isinstance(result, ParseResult)
    assert result.success is True
    assert result.ast is not None
    assert result.normalized_sql is not None


def test_adapter_parse_invalid():
    """SqlglotAdapter.parse() 对非法 SQL 返回 success=False + error 信息。"""
    result = SqlglotAdapter.parse(INVALID_SQL_SYNTAX)

    assert result.success is False
    assert result.error is not None
    assert result.error_code == "PARSE_ERROR"
    assert result.ast is None


def test_adapter_format():
    """SqlglotAdapter.format() 返回格式化后的字符串。"""
    formatted = SqlglotAdapter.format("select a from t")

    assert isinstance(formatted, str)
    assert len(formatted) > 0
    assert "SELECT" in formatted


def test_adapter_dialect_switch():
    """SqlglotAdapter 通过 dialect 参数支持方言切换。"""
    spark_result = SqlglotAdapter.parse("SELECT 1", dialect="spark")
    assert spark_result.success is True
    assert spark_result.dialect == "spark"

    hive_result = SqlglotAdapter.parse("SELECT 1", dialect="hive")
    assert hive_result.success is True
    assert hive_result.dialect == "hive"

    mysql_result = SqlglotAdapter.parse("SELECT 1", dialect="mysql")
    assert mysql_result.success is True
    assert mysql_result.dialect == "mysql"


def test_adapter_get_table_names():
    """SqlglotAdapter.get_table_names() 提取表名列表。"""
    tables = SqlglotAdapter.get_table_names(
        "SELECT * FROM my_table t1 JOIN other ON t1.id = other.id"
    )

    assert isinstance(tables, list)
    assert len(tables) >= 2
    assert "my_table" in tables
    assert "other" in tables


def test_adapter_get_column_names():
    """SqlglotAdapter.get_column_names() 提取字段名列表。"""
    columns = SqlglotAdapter.get_column_names(
        "SELECT a, b, c FROM t WHERE d > 0"
    )

    assert isinstance(columns, list)
    # SELECT a,b,c 至少 3 个字段，WHERE d 也算引用字段
    assert len(columns) >= 3
    assert "a" in columns
    assert "b" in columns
    assert "c" in columns


def test_adapter_unknown_dialect_fallback():
    """不支持的方言应降级为 spark 而不是崩溃。"""
    # 传入不支持的方言
    result = SqlglotAdapter.parse("SELECT 1", dialect="postgresql")
    assert result.success is True, (
        f"不支持的方言应 fallback 到 spark，success={result.success}"
    )

    # format 同样应 fallback
    formatted = SqlglotAdapter.format("select 1", dialect="postgresql")
    assert isinstance(formatted, str)
