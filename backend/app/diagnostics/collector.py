"""Small diagnostics collector with deterministic IDs and ordering."""

from __future__ import annotations

import itertools

from app.domain.contracts import (
    Diagnostic,
    DiagnosticCode,
    DiagnosticLevel,
    DiagnosticsReport,
)


class DiagnosticsCollector:
    def __init__(self) -> None:
        self._counter = itertools.count(1)
        self._diagnostics: list[Diagnostic] = []
        self._keys: set[tuple] = set()

    def add(
        self,
        code: DiagnosticCode,
        level: DiagnosticLevel,
        message: str,
        *,
        suggestion: str | None = None,
        source_location_id: str | None = None,
        related_entity_ids: list[str] | None = None,
        details: dict | None = None,
    ) -> Diagnostic:
        related = related_entity_ids or []
        key = (code, level, source_location_id, tuple(sorted(related)), message)
        if key in self._keys:
            return next(d for d in self._diagnostics if (
                d.code,
                d.level,
                d.source_location_id,
                tuple(sorted(d.related_entity_ids)),
                d.message,
            ) == key)
        self._keys.add(key)
        diagnostic = Diagnostic(
            diagnostic_id=f"diag:{code.value}:{next(self._counter)}",
            code=code,
            level=level,
            message=message,
            suggestion=suggestion,
            source_location_id=source_location_id,
            related_entity_ids=related,
            details=details or {},
        )
        self._diagnostics.append(diagnostic)
        return diagnostic

    def extend(self, diagnostics: list[Diagnostic]) -> None:
        for diagnostic in diagnostics:
            key = (
                diagnostic.code,
                diagnostic.level,
                diagnostic.source_location_id,
                tuple(sorted(diagnostic.related_entity_ids)),
                diagnostic.message,
            )
            if key not in self._keys:
                self._keys.add(key)
                self._diagnostics.append(diagnostic)

    def list(self) -> list[Diagnostic]:
        rank = {
            DiagnosticLevel.error: 0,
            DiagnosticLevel.warning: 1,
            DiagnosticLevel.info: 2,
        }
        return sorted(self._diagnostics, key=lambda d: (rank[d.level], d.diagnostic_id))

    def report(self) -> DiagnosticsReport:
        diagnostics = self.list()
        return DiagnosticsReport(
            diagnostics=diagnostics,
            error_count=sum(1 for d in diagnostics if d.level == DiagnosticLevel.error),
            warning_count=sum(1 for d in diagnostics if d.level == DiagnosticLevel.warning),
            info_count=sum(1 for d in diagnostics if d.level == DiagnosticLevel.info),
        )
