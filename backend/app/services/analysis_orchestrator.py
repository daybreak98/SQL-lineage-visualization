"""P0 analyze orchestration pipeline."""

from __future__ import annotations

import time
from uuid import uuid4

from app.diagnostics.collector import DiagnosticsCollector
from app.domain.contracts import (
    AnalysisStatus,
    AnalyzeSqlRequest,
    Diagnostic,
    DiagnosticCode,
    DiagnosticLevel,
    Dialect,
    EntityType,
    GraphViewModel,
    LineageIR,
    LineageNodeType,
    MetadataContext,
    SemanticsReport,
    StageState,
)
from app.services.source_location_extractor import SourceLocationExtractor
from app.repositories.metadata_repository import MetadataRepository
from app.services.contract_assembler import ContractAssembler
from app.services.graph_builder import GraphBuilder
from app.services.lineage_engine import LineageEngine
from app.services.metadata_service import MetadataService
from app.services.name_resolver import NameResolver
from app.services.expression_analyzer import ExpressionAnalyzer
from app.services.projection_extractor import ProjectionExtractor
from app.services.scope_resolver import ScopeResolver
from app.services.sql_parse_service import SqlParseService
from app.services.stage_status_builder import StageStatusBuilder
from app.services.star_expander import StarExpander
from app.services.semantics_analyzer import SemanticsAnalyzer
from app.domain.semantics_model import SemanticsAnalysisResult


class AnalysisOrchestrator:
    def __init__(self, repo: MetadataRepository | None = None):
        self.repo = repo or MetadataRepository()
        self.sql_parse_service = SqlParseService()
        self.scope_resolver = ScopeResolver()
        self.metadata_service = MetadataService(self.repo)
        self.name_resolver = NameResolver(self.metadata_service)
        self.star_expander = StarExpander(self.metadata_service)
        self.projection_extractor = ProjectionExtractor()
        self.expression_analyzer = ExpressionAnalyzer()
        self.lineage_engine = LineageEngine()
        self.graph_builder = GraphBuilder()
        self.contract_assembler = ContractAssembler()
        self.source_location_extractor = SourceLocationExtractor()
        self.semantics_analyzer = SemanticsAnalyzer()

    def analyze(self, request: AnalyzeSqlRequest):
        started = time.perf_counter()
        analysis_id = f"analysis:{uuid4().hex[:12]}"
        stages = StageStatusBuilder()
        diagnostics = DiagnosticsCollector()
        dialect = request.dialect if isinstance(request.dialect, Dialect) else Dialect(request.dialect)

        stages.start("parse")
        parse_result, parse_diagnostics = self.sql_parse_service.parse(
            request.sql,
            dialect.value,
        )
        diagnostics.extend(parse_diagnostics)
        if not parse_result.success:
            stages.finish("parse", StageState.failed, parse_diagnostics, "SQL parse failed")
            for stage in ["source_location", "scope", "name_resolution", "projection", "lineage", "graph", "semantics"]:
                stages.skipped(stage, "Skipped because parse failed", parse_diagnostics)
            report = diagnostics.report()
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return self.contract_assembler.assemble(
                analysis_id=analysis_id,
                status=AnalysisStatus.failed,
                dialect=dialect,
                normalized_sql=None,
                metadata_context=self._empty_metadata_context(request),
                lineage_ir=LineageIR(confidence_reasons=["SQL 解析失败"]),
                graph_view_model=GraphViewModel(),
                diagnostics_report=report,
                source_locations=[],
                stage_statuses=stages.all(),
                unsupported_features=[],
                elapsed_ms=elapsed_ms,
            )
        stages.finish("parse", StageState.success, parse_diagnostics)

        stages.start("scope")
        scope_model, scope_diagnostics = self.scope_resolver.resolve(
            parse_result,
            default_catalog=request.default_catalog,
            default_schema=request.default_schema,
        )
        diagnostics.extend(scope_diagnostics)
        stages.finish(
            "scope",
            StageState.partial if scope_diagnostics else StageState.success,
            scope_diagnostics,
        )

        stages.start("name_resolution")
        name_resolution, name_diagnostics = self.name_resolver.resolve(
            scope_model,
            metadata_version=request.metadata_version,
            default_catalog=request.default_catalog,
            default_schema=request.default_schema,
            case_sensitive=request.case_sensitive,
        )
        diagnostics.extend(name_diagnostics)
        name_stage_state = self._stage_state(name_diagnostics)
        stages.finish(
            "name_resolution",
            name_stage_state,
            name_diagnostics,
        )

        if name_stage_state == StageState.failed:
            for stage in ["projection", "lineage", "source_location", "graph", "semantics"]:
                stages.skipped(stage, "Skipped because name resolution failed", name_diagnostics)
            report = diagnostics.report()
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return self.contract_assembler.assemble(
                analysis_id=analysis_id,
                status=AnalysisStatus.failed,
                dialect=dialect,
                normalized_sql=parse_result.normalized_sql,
                metadata_context=name_resolution.metadata_context,
                lineage_ir=LineageIR(confidence_reasons=["Name resolution failed"]),
                graph_view_model=GraphViewModel(),
                diagnostics_report=report,
                source_locations=[],
                stage_statuses=stages.all(),
                unsupported_features=[],
                elapsed_ms=elapsed_ms,
            )

        # ── M20 (R11a): star expansion ──
        expanded_items, star_resolved_columns, star_diagnostics = self.star_expander.expand(
            scope_model,
            name_resolution,
            metadata_version=request.metadata_version,
        )
        diagnostics.extend(star_diagnostics)
        # Merge star-expanded column resolutions into name_resolution for projection extraction
        if star_resolved_columns:
            enhanced_resolution = name_resolution.model_copy(update={
                "resolved_columns": name_resolution.resolved_columns + star_resolved_columns,
            })
        else:
            enhanced_resolution = name_resolution

        stages.start("projection")
        projection_model = self.projection_extractor.extract(
            scope_model,
            enhanced_resolution,
            expanded_select_items=expanded_items,
        )
        projection_diagnostics = self._projection_diagnostics(projection_model.unsupported_expressions)
        diagnostics.extend(projection_diagnostics)
        stages.finish(
            "projection",
            StageState.partial if projection_diagnostics else StageState.success,
            projection_diagnostics,
        )

        # ── M23 (R13a): expression analysis ──
        stages.start("expression_analysis")
        expression_model = self.expression_analyzer.analyze(
            parse_result, projection_model, scope_model,
        )
        stages.finish("expression_analysis", StageState.success, [])

        stages.start("lineage")
        lineage_ir = self.lineage_engine.build(
            scope_model, enhanced_resolution, projection_model,
            expression_model=expression_model,
        )
        stages.finish(
            "lineage",
            StageState.partial if lineage_ir.partial else StageState.success,
            [],
        )

        stages.start("source_location")
        source_locations: list = []
        location_diagnostics: list[Diagnostic] = []
        if request.analysis_options.include_source_location:
            source_locations, location_diagnostics = self.source_location_extractor.extract(
                request.sql, parse_result, scope_model, name_resolution,
            )
            # 将 source_location_id 绑定到 lineage_ir 节点（向后兼容）
            location_by_entity: dict[str, str] = {}
            for loc in source_locations:
                if loc.range_type == "exact" and loc.location_id:
                    location_by_entity.setdefault(loc.entity_id, loc.location_id)
            for node in lineage_ir.nodes:
                if node.id in location_by_entity:
                    node.source_location_id = location_by_entity[node.id]
        diagnostics.extend(location_diagnostics)
        stages.finish("source_location", StageState.success, location_diagnostics)

        stages.start("graph")
        graph = self.graph_builder.build(lineage_ir) if request.analysis_options.include_graph else GraphViewModel()
        stages.finish("graph", StageState.success, [])

        # ── M25 Semantics Analysis ──
        stages.start("semantics")
        semantics_report: SemanticsReport
        if request.analysis_options.include_semantics:
            semantics_result = self.semantics_analyzer.analyze(
                expression_model=projection_model,
                lineage_ir=lineage_ir,
                metadata_context=enhanced_resolution.metadata_context,
                scope_model=scope_model,
                parse_result=parse_result,
                source_locations=source_locations,
            )
            semantics_report = self._to_semantics_report(semantics_result)
            stages.finish(
                "semantics",
                StageState.partial if semantics_result.status == "partial" else StageState.success,
                [],
            )
        else:
            semantics_report = SemanticsReport(status="not_supported_in_p0")
            stages.skipped("semantics", "SemanticsReport is not supported in P0 (enable via analysis_options.include_semantics)")

        report = diagnostics.report()
        status = self._analysis_status(report.diagnostics)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return self.contract_assembler.assemble(
            analysis_id=analysis_id,
            status=status,
            dialect=dialect,
            normalized_sql=parse_result.normalized_sql,
            metadata_context=name_resolution.metadata_context,
            lineage_ir=lineage_ir,
            graph_view_model=graph,
            diagnostics_report=report,
            source_locations=source_locations,
            stage_statuses=stages.all(),
            unsupported_features=projection_model.unsupported_expressions,
            elapsed_ms=elapsed_ms,
            semantics_report=semantics_report,
        )

    @staticmethod
    def _empty_metadata_context(request: AnalyzeSqlRequest) -> MetadataContext:
        return MetadataContext(
            metadata_version=request.metadata_version,
            case_sensitive=request.case_sensitive,
            default_catalog=request.default_catalog,
            default_schema=request.default_schema,
        )

    @staticmethod
    def _stage_state(diagnostics: list[Diagnostic]) -> StageState:
        if any(d.level == DiagnosticLevel.error for d in diagnostics):
            return StageState.failed
        if diagnostics:
            return StageState.partial
        return StageState.success

    @staticmethod
    def _analysis_status(diagnostics: list[Diagnostic]) -> AnalysisStatus:
        if any(d.code == DiagnosticCode.PARSE_ERROR for d in diagnostics):
            return AnalysisStatus.failed
        # UNKNOWN_TABLE is now a warning, treat as partial not failed
        if any(d.code == DiagnosticCode.UNKNOWN_TABLE for d in diagnostics):
            return AnalysisStatus.partial
        if any(d.level == DiagnosticLevel.error for d in diagnostics):
            return AnalysisStatus.failed
        if any(d.level == DiagnosticLevel.warning for d in diagnostics):
            return AnalysisStatus.partial
        if diagnostics:
            return AnalysisStatus.partial
        return AnalysisStatus.success

    @staticmethod
    def _to_semantics_report(result: SemanticsAnalysisResult) -> SemanticsReport:
        """Convert internal SemanticsAnalysisResult to API SemanticsReport."""
        return SemanticsReport(
            status=result.status,
            result_grain=result.result_grain.model_dump() if result.result_grain else None,
            filters=[f.model_dump() for f in result.filters],
            metrics=[m.model_dump() for m in result.metrics],
            joins=[j.model_dump() for j in result.joins],
            windows=[],
            dedup_logic=[d.model_dump() for d in result.dedup_logic],
            semantic_risks=[r.model_dump() for r in result.semantic_risks],
            evidence_refs=result.evidence_refs,
        )

    @staticmethod
    def _projection_diagnostics(unsupported: list[str]) -> list[Diagnostic]:
        return [
            Diagnostic(
                diagnostic_id=f"diag:NOT_SUPPORTED_IN_P0:{index}",
                code=DiagnosticCode.NOT_SUPPORTED_IN_P0,
                level=DiagnosticLevel.info,
                message=f"P0 暂不支持完整表达式血缘: {expression}",
                suggestion="当前结果会保留输出字段并降级为 partial/unknown，复杂表达式请在 P2 ExpressionAnalyzer 中增强",
                details={"expression": expression},
            )
            for index, expression in enumerate(unsupported, start=1)
        ]
