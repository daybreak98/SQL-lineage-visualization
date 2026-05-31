"""UTF-16 coordinate helpers compatible with Monaco editor positions."""

from __future__ import annotations

import hashlib


def utf16_code_units(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def source_sql_id(sql: str) -> str:
    return "sql:" + hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def line_start_offsets_utf16(text: str) -> list[int]:
    starts = [0]
    offset = 0
    for line in text.splitlines(keepends=True):
        offset += utf16_code_units(line)
        starts.append(offset)
    if text and not text.endswith(("\n", "\r")):
        starts.pop()
    return starts


def utf16_offset_to_line_col(text: str, offset: int) -> tuple[int, int]:
    if offset < 0:
        raise ValueError("offset must be >= 0")
    total = utf16_code_units(text)
    if offset > total:
        raise ValueError("offset exceeds text length")

    starts = line_start_offsets_utf16(text)
    line_index = 0
    for idx, start in enumerate(starts):
        if start <= offset:
            line_index = idx
        else:
            break
    line_start = starts[line_index]
    return line_index + 1, offset - line_start + 1


def line_col_to_utf16_offset(text: str, line: int, col: int) -> int:
    if line < 1 or col < 1:
        raise ValueError("line and col are 1-based")
    starts = line_start_offsets_utf16(text)
    if line > len(starts):
        raise ValueError("line exceeds text line count")
    offset = starts[line - 1] + col - 1
    if offset > utf16_code_units(text):
        raise ValueError("line/col exceeds text length")
    return offset


def python_index_to_utf16_offset(text: str, index: int) -> int:
    if index < 0 or index > len(text):
        raise ValueError("index out of range")
    return utf16_code_units(text[:index])


def utf16_range_for_text(text: str, raw_text: str) -> tuple[int, int] | None:
    index = text.find(raw_text)
    if index < 0:
        return None
    start = python_index_to_utf16_offset(text, index)
    end = start + utf16_code_units(raw_text)
    return start, end
