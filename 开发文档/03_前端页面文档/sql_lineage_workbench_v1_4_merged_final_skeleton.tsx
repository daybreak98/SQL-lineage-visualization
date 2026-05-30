import React from "react";

/**
 * SQL Lineage Workbench v1.4 Merged Final Skeleton
 *
 * Scope: v1.3 P0-Core + v1.4 UI/UX merge.
 * Not a v1.5 feature expansion.
 */

export type PageMode = "empty" | "ready" | "analyzing" | "analyzed" | "dirty" | "failed";
export type AnalysisStatus = "none" | "running" | "success" | "partial" | "failed" | "cancelled" | "timeout";
export type TrustStatus = "trusted" | "stale" | "untrusted";
export type StaleReason = "sql_changed" | "metadata_changed" | "analysis_expired";

export interface WorkbenchRuntimeState {
  pageMode: PageMode;
  analysisStatus: AnalysisStatus;
  trustStatus: TrustStatus;
  analysisId?: string;
  sqlHash?: string;
  metadataVersion?: string;
  staleReason?: StaleReason;
  lastTrustedAnalysisId?: string;
  lastTrustedSqlHash?: string;
}

export type GraphRenderMode =
  | "subquery_dependency"
  | "current_field_path"
  | "focus_field"
  | "semantic_mode"
  | "large_graph"
  | "full_graph_preview";

export interface GraphRenderModeTransition {
  from: GraphRenderMode;
  event:
    | "ANALYZE_SUCCESS"
    | "SELECT_OUTPUT_FIELD"
    | "FOCUS_FIELD"
    | "OPEN_SEMANTIC_MODE"
    | "ENTER_LARGE_GRAPH"
    | "OPEN_FULL_PREVIEW"
    | "CLEAR_SELECTION"
    | "REANALYZE"
    | "ANALYZE_FAILED";
  to: GraphRenderMode;
  preserveViewport: boolean;
  recomputeLayout: boolean;
}

export const graphRenderTransitions: GraphRenderModeTransition[] = [
  { from: "subquery_dependency", event: "ANALYZE_SUCCESS", to: "subquery_dependency", preserveViewport: false, recomputeLayout: true },
  { from: "subquery_dependency", event: "SELECT_OUTPUT_FIELD", to: "current_field_path", preserveViewport: false, recomputeLayout: false },
  { from: "current_field_path", event: "FOCUS_FIELD", to: "focus_field", preserveViewport: true, recomputeLayout: false },
  { from: "current_field_path", event: "OPEN_SEMANTIC_MODE", to: "semantic_mode", preserveViewport: true, recomputeLayout: false },
  { from: "current_field_path", event: "ENTER_LARGE_GRAPH", to: "large_graph", preserveViewport: true, recomputeLayout: false },
  { from: "subquery_dependency", event: "OPEN_FULL_PREVIEW", to: "full_graph_preview", preserveViewport: false, recomputeLayout: true },
  { from: "current_field_path", event: "CLEAR_SELECTION", to: "subquery_dependency", preserveViewport: false, recomputeLayout: false },
];

export interface PathContextStore {
  selectedOutputEntityId?: string;
  selectedOutputDisplayName?: string;
  pathMode: "none" | "upstream" | "downstream" | "full";
  pathStatus: "idle" | "ready" | "partial" | "stale" | "low_confidence" | "failed";
  pathRef?: unknown;
  nodeCount?: number;
  mappingCount?: number;
  warningCount?: number;
  unresolvedCount?: number;
  confidenceLevel?: "high" | "medium" | "low" | "unknown";
  staleReason?: StaleReason;
}

export interface SubqueryDependencyViewModel {
  renderMode: "subquery_dependency";
  nodes: Array<TableSummaryNode | CteSummaryNode | SubquerySummaryNode | OutputGroupNode | OutputFieldNode | ExpressionGroupNode>;
  edges: DependencySummaryEdge[];
  hiddenFieldEntityIds: string[];
  hiddenSemanticEdgeIds: string[];
  defaultOutputEntityIds: string[];
  diagnosticsSummary: DiagnosticsSummary;
}

export interface TableSummaryNode { entityId: string; nodeType: "table"; label: string; alias?: string; schemaShort?: string; }
export interface CteSummaryNode { entityId: string; nodeType: "cte"; label: string; badges?: string[]; }
export interface SubquerySummaryNode { entityId: string; nodeType: "subquery"; label: string; stableIndex?: number; badges?: Array<"agg" | "join" | "filter" | "group by">; }
export interface OutputGroupNode { entityId: string; nodeType: "output_group"; outputCount: number; warningCount?: number; }
export interface OutputFieldNode { entityId: string; nodeType: "output_field"; label: string; }
export interface ExpressionGroupNode { entityId: string; nodeType: "expression"; expressionType: "CASE" | "SUM" | "COUNT" | "WINDOW" | "ARITH"; }
export interface DependencySummaryEdge { edgeId: string; sourceEntityId: string; targetEntityId: string; edgeType: "table_to_block" | "block_to_block" | "block_to_output" | "expression_to_output"; mappingCount?: number; }
export interface DiagnosticsSummary { warningCount: number; errorCount: number; unresolvedCount: number; }

export type NodeVisualType = "output" | "output_field" | "subquery" | "cte" | "table" | "expression" | "join_filter" | "unknown";
export type NodeVisualState = "selected" | "error" | "current_path" | "search_hit" | "warning" | "stale" | "hover" | "dimmed" | "normal";

export const nodeStatePriority: NodeVisualState[] = [
  "selected",
  "error",
  "current_path",
  "search_hit",
  "warning",
  "stale",
  "hover",
  "dimmed",
  "normal",
];

export interface AttentionViewModel {
  primaryFocus:
    | "empty_guide"
    | "analyze"
    | "search_default_output"
    | "current_path"
    | "detail_mapping"
    | "monaco_range"
    | "re_analyze"
    | "error_summary";
  taskStage:
    | "empty"
    | "ready"
    | "analyzing"
    | "analyzed_no_field"
    | "path_selected"
    | "object_selected"
    | "locating_sql"
    | "dirty"
    | "failed";
  reason: string;
  source: "page_mode" | "path_context" | "selection" | "diagnostic" | "editor_dirty";
}

export interface DiagnosticAttentionRule {
  diagnosticCode: string;
  defaultSeverity: "info" | "warning" | "error";
  attentionLevel: "L1" | "L2" | "L3" | "L4";
  blocking: boolean;
  placement:
    | "canvas_error_summary"
    | "path_anchor"
    | "detail_panel"
    | "status_strip"
    | "diagnostics_drawer"
    | "editor_marker"
    | "search_result_row";
  recommendedAction?: "locate_sql" | "view_mapping" | "reanalyze" | "check_metadata" | "switch_scope" | "view_diagnostics";
}

export const visualRegressionSnapshots = [
  "snapshot-01-ready-analyze-cta",
  "snapshot-02-analyzed-subquery-dependency",
  "snapshot-03-selected-current-field-path",
  "snapshot-04-detailpanel-compact-edge-mapping",
  "snapshot-05-dirty-reanalyze-stale",
  "snapshot-06-failed-error-summary",
  "snapshot-07-large-graph-subquery-summary",
  "snapshot-08-node-taxonomy-100-nodes",
  "snapshot-09-toolbar-deduplication",
  "snapshot-10-1366-canvas-space-budget",
] as const;

export function selectAttentionViewModel(args: {
  runtime: WorkbenchRuntimeState;
  pathContext: PathContextStore;
  selectedEntityId?: string;
  selectedEdgeMappingId?: string;
  detailOpen: boolean;
  revealingSql: boolean;
}): AttentionViewModel {
  const { runtime, pathContext, selectedEntityId, selectedEdgeMappingId, detailOpen, revealingSql } = args;
  if (runtime.pageMode === "empty") return { primaryFocus: "empty_guide", taskStage: "empty", reason: "No SQL", source: "page_mode" };
  if (runtime.pageMode === "ready") return { primaryFocus: "analyze", taskStage: "ready", reason: "SQL ready", source: "page_mode" };
  if (runtime.pageMode === "analyzing") return { primaryFocus: "analyze", taskStage: "analyzing", reason: "Analysis running", source: "page_mode" };
  if (runtime.pageMode === "failed") return { primaryFocus: "error_summary", taskStage: "failed", reason: "Analysis failed", source: "diagnostic" };
  if (runtime.pageMode === "dirty" || runtime.trustStatus === "stale") return { primaryFocus: "re_analyze", taskStage: "dirty", reason: "SQL changed", source: "editor_dirty" };
  if (revealingSql) return { primaryFocus: "monaco_range", taskStage: "locating_sql", reason: "Locate SQL", source: "selection" };
  if (selectedEdgeMappingId) return { primaryFocus: "detail_mapping", taskStage: "object_selected", reason: "Mapping selected", source: "selection" };
  if (selectedEntityId && detailOpen) return { primaryFocus: "detail_mapping", taskStage: "object_selected", reason: "Entity selected", source: "selection" };
  if (pathContext.selectedOutputEntityId) return { primaryFocus: "current_path", taskStage: "path_selected", reason: "Current path selected", source: "path_context" };
  return { primaryFocus: "search_default_output", taskStage: "analyzed_no_field", reason: "Choose output", source: "path_context" };
}

export default function SqlLineageWorkbenchV14MergedFinal() {
  return (
    <div>
      <h1>SQL Lineage Workbench v1.4 Merged Final</h1>
      <p>
        Implement v1.3 P0-Core with default Subquery Dependency View, Node Visual Taxonomy,
        GraphRenderMode State Machine, Toolbar Deduplication and Canvas Space Budget.
      </p>
    </div>
  );
}
