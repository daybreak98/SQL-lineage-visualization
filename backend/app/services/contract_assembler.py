"""Assemble the public AnalysisResult contract."""

from __future__ import annotations

from app.domain.contracts import (
    AnalysisResult,
    AnalysisStatus,
    AnalysisSummary,
    ConfidenceLevel,
    DiagnosticsReport,
    Dialect,
    GraphViewModel,
    LineageIR,
    LineageNodeType,
    MetadataContext,
    SemanticsReport,
    SourceLocation,
    StageStatus,
)


class ContractAssembler:
    def assemble(
        self,
        *,
        analysis_id: str,
        status: AnalysisStatus,
        dialect: Dialect,
        normalized_sql: str | None,
        metadata_context: MetadataContext,
        lineage_ir: LineageIR,
        graph_view_model: GraphViewModel,
        diagnostics_report: DiagnosticsReport,
        source_locations: list[SourceLocation],
        stage_statuses: list[StageStatus],
        unsupported_features: list[str],
        elapsed_ms: int,
    ) -> AnalysisResult:
        return AnalysisResult(
            analysis_id=analysis_id,
            status=status,
            confidence_level=self._confidence(status, lineage_ir.confidence_level),
            confidence_reasons=lineage_ir.confidence_reasons,
            stage_statuses=stage_statuses,
            unsupported_features=unsupported_features,
            elapsed_ms=elapsed_ms,
            dialect=dialect,
            normalized_sql=normalized_sql,
            metadata_context=metadata_context,
            lineage_ir=lineage_ir,
            semantics_report=SemanticsReport(status="not_supported_in_p0"),
            diagnostics_report=diagnostics_report,
            graph_view_model=graph_view_model,
            source_locations=source_locations,
            summary=self._summary(metadata_context, lineage_ir, diagnostics_report),
        )

    @staticmethod
    def _confidence(status: AnalysisStatus, lineage_confidence: ConfidenceLevel) -> ConfidenceLevel:
        if status == AnalysisStatus.failed:
            return ConfidenceLevel.low
        if status == AnalysisStatus.partial:
            return ConfidenceLevel.medium
        return lineage_confidence

    @staticmethod
    def _summary(
        metadata_context: MetadataContext,
        lineage_ir: LineageIR,
        diagnostics_report: DiagnosticsReport,
    ) -> AnalysisSummary:
        return AnalysisSummary(
            table_count=len(metadata_context.resolved_tables),
            source_column_count=sum(1 for n in lineage_ir.nodes if n.node_type == LineageNodeType.column),
            output_column_count=sum(1 for n in lineage_ir.nodes if n.node_type == LineageNodeType.output_column),
            lineage_edge_count=len(lineage_ir.edges),
            diagnostic_count=len(diagnostics_report.diagnostics),
        )
