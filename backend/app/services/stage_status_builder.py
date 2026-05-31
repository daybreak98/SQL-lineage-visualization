"""Stage status collection for the analyze orchestrator."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.domain.contracts import Diagnostic, DiagnosticCode, StageState, StageStatus


@dataclass
class _StageTimer:
    stage: str
    started_at: float = field(default_factory=time.perf_counter)


class StageStatusBuilder:
    def __init__(self) -> None:
        self._statuses: list[StageStatus] = []
        self._active: dict[str, _StageTimer] = {}

    def start(self, stage: str) -> None:
        self._active[stage] = _StageTimer(stage=stage)

    def finish(
        self,
        stage: str,
        status: StageState,
        diagnostics: list[Diagnostic] | None = None,
        message: str | None = None,
    ) -> None:
        timer = self._active.pop(stage, None)
        elapsed_ms = 0
        if timer is not None:
            elapsed_ms = int((time.perf_counter() - timer.started_at) * 1000)
        self._statuses.append(
            StageStatus(
                stage=stage,
                status=status,
                elapsed_ms=max(elapsed_ms, 0),
                diagnostic_codes=self._codes(diagnostics or []),
                message=message,
            )
        )

    def skipped(
        self,
        stage: str,
        message: str,
        diagnostics: list[Diagnostic] | None = None,
    ) -> None:
        self._statuses.append(
            StageStatus(
                stage=stage,
                status=StageState.skipped,
                elapsed_ms=0,
                diagnostic_codes=self._codes(diagnostics or []),
                message=message,
            )
        )

    def all(self) -> list[StageStatus]:
        return list(self._statuses)

    @staticmethod
    def _codes(diagnostics: list[Diagnostic]) -> list[DiagnosticCode]:
        seen: set[DiagnosticCode] = set()
        ordered: list[DiagnosticCode] = []
        for diagnostic in diagnostics:
            if diagnostic.code not in seen:
                ordered.append(diagnostic.code)
                seen.add(diagnostic.code)
        return ordered
