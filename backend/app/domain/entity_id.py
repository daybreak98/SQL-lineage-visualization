"""Stable entity ID helpers for P0 analysis modules."""

from __future__ import annotations

import hashlib
import re


_SAFE_SEGMENT = re.compile(r"^[a-z0-9_:-]+$")


def normalize_name(value: str | None, *, case_sensitive: bool = False) -> str:
    """Normalize SQL object names without losing user-facing identity."""
    text = (value or "").strip().strip("`").strip('"')
    return text if case_sensitive else text.lower()


def safe_segment(value: str | None, *, case_sensitive: bool = False) -> str:
    normalized = normalize_name(value, case_sensitive=case_sensitive)
    normalized = normalized.replace(".", "_").replace(" ", "_")
    if normalized and _SAFE_SEGMENT.match(normalized):
        return normalized
    digest = hashlib.sha1((value or "").encode("utf-8")).hexdigest()[:10]
    return f"h_{digest}"


def hash_name(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


class EntityIdFactory:
    """Generate repeatable IDs shared by scope, lineage and graph modules."""

    @staticmethod
    def table(catalog: str, schema: str, table: str) -> str:
        cat = safe_segment(catalog)
        sch = safe_segment(schema)
        tbl = safe_segment(table)
        if cat == "default" or not cat:
            return f"table:{sch}.{tbl}"
        return f"table:{cat}.{sch}.{tbl}"

    @staticmethod
    def column(catalog: str, schema: str, table: str, column: str) -> str:
        cat = safe_segment(catalog)
        sch = safe_segment(schema)
        tbl = safe_segment(table)
        col = safe_segment(column)
        if cat == "default" or not cat:
            return f"column:{sch}.{tbl}.{col}"
        return f"column:{cat}.{sch}.{tbl}.{col}"

    @staticmethod
    def scope(scope_name: str = "root") -> str:
        return f"scope:{safe_segment(scope_name)}"

    @staticmethod
    def scope_relation(scope_id: str, alias: str) -> str:
        return f"scope_relation:{safe_segment(scope_id)}:{safe_segment(alias)}"

    @staticmethod
    def scope_column(scope_id: str, relation_alias: str, column: str) -> str:
        return (
            f"scope_column:{safe_segment(scope_id)}:"
            f"{safe_segment(relation_alias)}.{safe_segment(column)}"
        )

    @staticmethod
    def output_column(scope_id: str, output_name: str, ordinal: int) -> str:
        return (
            f"output_column:{safe_segment(scope_id)}:"
            f"{ordinal}:{safe_segment(output_name)}"
        )

    @staticmethod
    def literal(scope_id: str, ordinal: int) -> str:
        return f"literal:{safe_segment(scope_id)}:{ordinal}"

    @staticmethod
    def unknown(scope_id: str, name: str, ordinal: int = 0) -> str:
        return f"unknown:{safe_segment(scope_id)}:{ordinal}:{safe_segment(name)}"

    @staticmethod
    def edge(edge_type: str, source: str, target: str) -> str:
        key = f"{edge_type}|{source}|{target}"
        return f"edge:{edge_type}:{hash_name(key)}"
