from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisStatus(str, Enum):
    success = "success"
    partial = "partial"
    failed = "failed"


class StageState(str, Enum):
    success = "success"
    partial = "partial"
    failed = "failed"
    skipped = "skipped"


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    unknown = "unknown"


class Dialect(str, Enum):
    spark = "spark"
    hive = "hive"
    mysql = "mysql"
    starrocks = "starrocks"
    doris = "doris"


class AnalysisLevel(str, Enum):
    table = "table"
    column = "column"
    expression = "expression"


class EntityType(str, Enum):
    statement = "statement"
    scope = "scope"
    table = "table"
    table_alias = "table_alias"
    column = "column"
    output_column = "output_column"
    expression = "expression"
    filter = "filter"
    join = "join"
    cte = "cte"
    subquery = "subquery"
    diagnostic = "diagnostic"
    unknown = "unknown"


class LineageNodeType(str, Enum):
    statement = "statement"
    scope = "scope"
    table = "table"
    column = "column"
    output_column = "output_column"
    expression = "expression"
    unknown = "unknown"


class LineageEdgeType(str, Enum):
    projection = "projection"
    alias = "alias"
    expression = "expression"
    filter_condition = "filter_condition"
    unknown = "unknown"


class GraphViewMode(str, Enum):
    table = "table"
    column = "column"
    expression = "expression"
    semantics = "semantics"
    diagnostics = "diagnostics"


class GraphNodeType(str, Enum):
    table = "table"
    column = "column"
    output_column = "output_column"
    expression = "expression"
    unknown = "unknown"
    diagnostic = "diagnostic"


class GraphEdgeType(str, Enum):
    projection = "projection"
    alias = "alias"
    expression = "expression"
    filter_condition = "filter_condition"
    unknown = "unknown"


class DiagnosticLevel(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"


class DiagnosticCode(str, Enum):
    PARSE_ERROR = "PARSE_ERROR"
    UNKNOWN_TABLE = "UNKNOWN_TABLE"
    UNKNOWN_COLUMN = "UNKNOWN_COLUMN"
    AMBIGUOUS_COLUMN = "AMBIGUOUS_COLUMN"
    STAR_EXPANSION_FAILED = "STAR_EXPANSION_FAILED"
    UNSUPPORTED_DIALECT_FEATURE = "UNSUPPORTED_DIALECT_FEATURE"
    MISSING_METADATA = "MISSING_METADATA"
    DUPLICATE_ALIAS = "DUPLICATE_ALIAS"
    METADATA_VERSION_MISMATCH = "METADATA_VERSION_MISMATCH"
    METADATA_IMPORT_INVALID_JSON = "METADATA_IMPORT_INVALID_JSON"
    METADATA_IMPORT_DUPLICATE_COLUMN = "METADATA_IMPORT_DUPLICATE_COLUMN"
    METADATA_IMPORT_SCHEMA_UNSUPPORTED = "METADATA_IMPORT_SCHEMA_UNSUPPORTED"
    METADATA_IMPORT_EMPTY_TABLE_NAME = "METADATA_IMPORT_EMPTY_TABLE_NAME"
    METADATA_IMPORT_EMPTY_COLUMNS = "METADATA_IMPORT_EMPTY_COLUMNS"
    METADATA_IMPORT_COMPLEX_TYPE = "METADATA_IMPORT_COMPLEX_TYPE"
    METADATA_IMPORT_MISSING_ORDINAL = "METADATA_IMPORT_MISSING_ORDINAL"
    METADATA_IMPORT_COMMIT_FAILED = "METADATA_IMPORT_COMMIT_FAILED"
    SOURCE_LOCATION_UNAVAILABLE = "SOURCE_LOCATION_UNAVAILABLE"
    NOT_SUPPORTED_IN_P0 = "NOT_SUPPORTED_IN_P0"


class MetadataObjectRef(StrictBaseModel):
    catalog: str = "default"
    schema: str = "default"
    table: str
    column: str | None = None


class SourceLocation(StrictBaseModel):
    location_id: str
    entity_id: str
    entity_type: EntityType
    source_sql_id: str | None = None
    range_type: Literal["exact", "synthetic", "unavailable"] = "unavailable"
    start_line: int | None = Field(default=None, ge=1)
    start_col: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    end_col: int | None = Field(default=None, ge=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    raw_text: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Diagnostic(StrictBaseModel):
    diagnostic_id: str
    code: DiagnosticCode
    level: DiagnosticLevel
    message: str
    suggestion: str | None = None
    source_location_id: str | None = None
    related_entity_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class DiagnosticsReport(StrictBaseModel):
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0


class StageStatus(StrictBaseModel):
    stage: str
    status: StageState
    elapsed_ms: int = Field(default=0, ge=0)
    diagnostic_codes: list[DiagnosticCode] = Field(default_factory=list)
    message: str | None = None


# Metadata import models
class MetadataColumnInput(StrictBaseModel):
    name: str = Field(min_length=1)
    data_type: str = "unknown"
    comment: str | None = None
    ordinal: int | None = Field(default=None, ge=1)
    is_partition: bool = False
    nullable: bool | None = None


class MetadataTableInput(StrictBaseModel):
    catalog: str = "default"
    schema: str = "default"
    name: str = Field(min_length=1)
    comment: str | None = None
    table_type: str = "table"
    columns: list[MetadataColumnInput] = Field(min_length=1)


class MetadataImportPayload(StrictBaseModel):
    schema_version: str = "1.0"
    metadata_version: str
    case_sensitive: bool = False
    default_catalog: str = "default"
    default_schema: str = "default"
    source_name: str | None = None
    tables: list[MetadataTableInput] = Field(min_length=1)


class ImportMode(str, Enum):
    preview = "preview"
    commit = "commit"


class MetadataImportRequest(StrictBaseModel):
    mode: ImportMode = ImportMode.preview
    payload: MetadataImportPayload


class ImportChangeType(str, Enum):
    added = "added"
    updated = "updated"
    unchanged = "unchanged"
    stale_candidate = "stale_candidate"
    conflict = "conflict"


class ImportStatus(str, Enum):
    preview_ready = "preview_ready"
    committed = "committed"
    failed = "failed"


class MetadataImportChange(StrictBaseModel):
    change_type: ImportChangeType
    object_type: Literal["table", "column"]
    object_ref: MetadataObjectRef
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    message: str | None = None


class MetadataImportResult(StrictBaseModel):
    status: ImportStatus
    import_batch_id: str | None = None
    metadata_version: str
    changes: list[MetadataImportChange] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class ResolvedTable(StrictBaseModel):
    entity_id: str
    catalog: str
    schema: str
    table: str
    alias: str | None = None
    columns: list[str] = Field(default_factory=list)


class MissingTable(StrictBaseModel):
    catalog: str
    schema: str
    table: str
    alias: str | None = None


class MissingColumn(StrictBaseModel):
    column: str
    scope_id: str = "scope:root"
    candidate_tables: list[str] = Field(default_factory=list)


class AmbiguousColumn(StrictBaseModel):
    column: str
    scope_id: str = "scope:root"
    candidate_columns: list[str] = Field(default_factory=list)


class MetadataContext(StrictBaseModel):
    metadata_version: str
    case_sensitive: bool = False
    default_catalog: str = "default"
    default_schema: str = "default"
    resolved_tables: list[ResolvedTable] = Field(default_factory=list)
    missing_tables: list[MissingTable] = Field(default_factory=list)
    missing_columns: list[MissingColumn] = Field(default_factory=list)
    ambiguous_columns: list[AmbiguousColumn] = Field(default_factory=list)


class AnalysisOptions(StrictBaseModel):
    include_graph: bool = True
    include_semantics: bool = False
    include_diagnostics: bool = True
    include_source_location: bool = True
    include_expression_lineage: bool = False


class AnalyzeSqlRequest(StrictBaseModel):
    sql: str = Field(min_length=1)
    dialect: Dialect = Dialect.spark
    analysis_level: AnalysisLevel = AnalysisLevel.column
    default_catalog: str = "default"
    default_schema: str = "default"
    metadata_version: str = "latest"
    case_sensitive: bool = False
    analysis_options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class ScopeItem(StrictBaseModel):
    scope_id: str
    parent_scope_id: str | None = None
    scope_type: Literal["root", "cte", "subquery"] = "root"
    table_aliases: dict[str, str] = Field(default_factory=dict)


class LineageNode(StrictBaseModel):
    id: str
    node_type: LineageNodeType
    label: str
    entity_type: EntityType
    metadata_ref: MetadataObjectRef | None = None
    scope_id: str = "scope:root"
    data_type: str | None = None
    comment: str | None = None
    expression: str | None = None
    source_location_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class LineageEdge(StrictBaseModel):
    id: str
    edge_type: LineageEdgeType
    source: str
    target: str
    label: str | None = None
    source_location_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    attributes: dict[str, Any] = Field(default_factory=dict)


class LineageIR(StrictBaseModel):
    scopes: list[ScopeItem] = Field(default_factory=list)
    nodes: list[LineageNode] = Field(default_factory=list)
    edges: list[LineageEdge] = Field(default_factory=list)
    partial: bool = False
    confidence_level: ConfidenceLevel = ConfidenceLevel.unknown
    confidence_reasons: list[str] = Field(default_factory=list)


class SemanticsReport(StrictBaseModel):
    status: Literal["not_supported_in_p0", "partial", "success"] = "not_supported_in_p0"
    result_grain: dict[str, Any] | None = None
    filters: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    joins: list[dict[str, Any]] = Field(default_factory=list)
    windows: list[dict[str, Any]] = Field(default_factory=list)
    dedup_logic: list[dict[str, Any]] = Field(default_factory=list)
    semantic_risks: list[dict[str, Any]] = Field(default_factory=list)


class GraphPosition(StrictBaseModel):
    x: float = 0
    y: float = 0


class GraphNode(StrictBaseModel):
    id: str
    entity_id: str | None = None
    node_type: GraphNodeType
    label: str
    position: GraphPosition = Field(default_factory=GraphPosition)
    source_location_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(StrictBaseModel):
    id: str
    edge_type: GraphEdgeType
    source: str
    target: str
    source_entity_id: str | None = None
    target_entity_id: str | None = None
    label: str | None = None
    source_location_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class GraphViewModel(StrictBaseModel):
    view_mode: GraphViewMode = GraphViewMode.column
    supported_view_modes: list[GraphViewMode] = Field(default_factory=lambda: [
        GraphViewMode.table, GraphViewMode.column, GraphViewMode.expression,
        GraphViewMode.semantics, GraphViewMode.diagnostics
    ])
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    selected_node_id: str | None = None
    highlighted_node_ids: list[str] = Field(default_factory=list)
    highlighted_edge_ids: list[str] = Field(default_factory=list)


class AnalysisSummary(StrictBaseModel):
    table_count: int = 0
    source_column_count: int = 0
    output_column_count: int = 0
    lineage_edge_count: int = 0
    diagnostic_count: int = 0


class AnalysisResult(StrictBaseModel):
    schema_version: str = "1.0"
    analysis_id: str
    status: AnalysisStatus
    confidence_level: ConfidenceLevel = ConfidenceLevel.unknown
    confidence_reasons: list[str] = Field(default_factory=list)
    stage_statuses: list[StageStatus] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    elapsed_ms: int = Field(default=0, ge=0)
    dialect: Dialect
    normalized_sql: str | None = None
    metadata_context: MetadataContext
    lineage_ir: LineageIR
    semantics_report: SemanticsReport = Field(default_factory=SemanticsReport)
    diagnostics_report: DiagnosticsReport = Field(default_factory=DiagnosticsReport)
    graph_view_model: GraphViewModel = Field(default_factory=GraphViewModel)
    source_locations: list[SourceLocation] = Field(default_factory=list)
    summary: AnalysisSummary = Field(default_factory=AnalysisSummary)


class FormatSqlRequest(StrictBaseModel):
    sql: str = Field(min_length=1)
    dialect: Dialect = Dialect.spark


class FormatSqlResponse(StrictBaseModel):
    status: AnalysisStatus
    dialect: Dialect
    formatted_sql: str | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)


class ApiError(StrictBaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(StrictBaseModel):
    error: ApiError


# ---------------------------------------------------------------------------
# 内部模型（不直接暴露给 API）
# ---------------------------------------------------------------------------

class ParseResult:
    """内部解析结果，不直接暴露 AST 给 API。"""

    def __init__(
        self,
        success: bool,
        ast=None,
        dialect: str = 'spark',
        normalized_sql: str | None = None,
        error: str | None = None,
        error_code: str | None = None,
    ):
        self.success = success
        self.ast = ast
        self.dialect = dialect
        self.normalized_sql = normalized_sql
        self.error = error
        self.error_code = error_code
