"""SourceLocation factories built on the M02 contract model."""

from __future__ import annotations

from app.domain.contracts import EntityType, SourceLocation
from app.domain.entity_id import hash_name
from app.utils.text_coordinates import (
    source_sql_id,
    utf16_offset_to_line_col,
    utf16_range_for_text,
)


def source_location_for_text(
    *,
    entity_id: str,
    entity_type: EntityType,
    sql: str,
    raw_text: str,
    confidence: float = 1.0,
) -> SourceLocation:
    found = utf16_range_for_text(sql, raw_text)
    if found is None:
        return synthetic_source_location(
            entity_id=entity_id,
            entity_type=entity_type,
            sql=sql,
            raw_text=raw_text,
            confidence=0.4,
        )
    start, end = found
    start_line, start_col = utf16_offset_to_line_col(sql, start)
    end_line, end_col = utf16_offset_to_line_col(sql, end)
    return SourceLocation(
        location_id=f"loc:{hash_name(entity_id + ':' + str(start) + ':' + str(end))}",
        entity_id=entity_id,
        entity_type=entity_type,
        source_sql_id=source_sql_id(sql),
        range_type="exact",
        start_line=start_line,
        start_col=start_col,
        end_line=end_line,
        end_col=end_col,
        start_offset=start,
        end_offset=end,
        raw_text=raw_text,
        confidence=confidence,
    )


def synthetic_source_location(
    *,
    entity_id: str,
    entity_type: EntityType,
    sql: str,
    raw_text: str | None = None,
    confidence: float = 0.3,
) -> SourceLocation:
    return SourceLocation(
        location_id=f"loc:synthetic:{hash_name(entity_id)}",
        entity_id=entity_id,
        entity_type=entity_type,
        source_sql_id=source_sql_id(sql),
        range_type="synthetic",
        raw_text=raw_text,
        confidence=confidence,
    )


def unavailable_source_location(
    *,
    entity_id: str,
    entity_type: EntityType,
    sql: str,
) -> SourceLocation:
    return SourceLocation(
        location_id=f"loc:unavailable:{hash_name(entity_id)}",
        entity_id=entity_id,
        entity_type=entity_type,
        source_sql_id=source_sql_id(sql),
        range_type="unavailable",
        confidence=0.0,
    )
