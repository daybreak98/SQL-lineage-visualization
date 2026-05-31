from app.domain.contracts import EntityType
from app.domain.source_location import source_location_for_text, synthetic_source_location
from app.utils.text_coordinates import (
    line_col_to_utf16_offset,
    source_sql_id,
    utf16_code_units,
    utf16_offset_to_line_col,
)


def test_utf16_counts_emoji_as_two_code_units():
    assert utf16_code_units("a😀b") == 4


def test_line_col_utf16_roundtrip_with_chinese_and_crlf():
    sql = "SELECT 名称\r\nFROM 用户表\r\nWHERE emoji_col = '😀'"
    offset = line_col_to_utf16_offset(sql, 3, 7)
    assert utf16_offset_to_line_col(sql, offset) == (3, 7)


def test_source_location_exact_range():
    sql = "SELECT 名称 FROM 用户表"
    location = source_location_for_text(
        entity_id="column:default.default.用户表.名称",
        entity_type=EntityType.column,
        sql=sql,
        raw_text="名称",
    )
    assert location.range_type == "exact"
    assert location.start_line == 1
    assert location.start_col == len("SELECT ") + 1
    assert location.source_sql_id == source_sql_id(sql)


def test_synthetic_location_serializes_without_offsets():
    location = synthetic_source_location(
        entity_id="output_column:scope:root:1:missing",
        entity_type=EntityType.output_column,
        sql="SELECT missing FROM t",
        raw_text="missing",
    )
    assert location.range_type == "synthetic"
    assert location.start_offset is None
    assert location.confidence < 1
