// §7.1
export type GraphRenderMode =
  | 'subquery_dependency'
  | 'current_field_path'
  | 'focus_field'
  | 'semantic_mode'
  | 'large_graph'
  | 'full_graph_preview';

// §7.2
export interface GraphRenderModeTransition {
  from: GraphRenderMode;
  event:
    | 'ANALYZE_SUCCESS'
    | 'SELECT_OUTPUT_FIELD'
    | 'FOCUS_FIELD'
    | 'OPEN_SEMANTIC_MODE'
    | 'ENTER_LARGE_GRAPH'
    | 'OPEN_FULL_PREVIEW'
    | 'CLEAR_SELECTION'
    | 'REANALYZE'
    | 'ANALYZE_FAILED';
  to: GraphRenderMode;
  preserveViewport: boolean;
  recomputeLayout: boolean;
}

// §8.2 SubqueryDependencyViewModel
export interface TableSummaryNode {
  id: string;
  entity_id: string;
  node_type: 'table';
  label: string;
  catalog: string;
  schema: string;
  table: string;
  alias?: string;
}

export interface CteSummaryNode {
  id: string;
  entity_id: string;
  node_type: 'cte';
  label: string;
  cte_name: string;
}

export interface SubquerySummaryNode {
  id: string;
  entity_id: string;
  node_type: 'subquery';
  label: string;
  alias?: string;
  subquery_n?: string;
  tags: string[];
}

export interface OutputGroupNode {
  id: string;
  entity_id: string;
  node_type: 'output_group';
  label: string;
  field_count: number;
  default_outputs: string[];
}

export interface OutputFieldNode {
  id: string;
  entity_id: string;
  node_type: 'output_field';
  label: string;
  data_type?: string;
}

export interface ExpressionGroupNode {
  id: string;
  entity_id: string;
  node_type: 'expression_group';
  label: string;
  expression_type: string;
}

export interface DependencySummaryEdge {
  id: string;
  edge_type: string;
  source: string;
  target: string;
  label?: string;
  field_count?: number;
}

export interface DiagnosticsSummary {
  error_count: number;
  warning_count: number;
  info_count: number;
  critical_codes: string[];
}

export interface SubqueryDependencyViewModel {
  renderMode: 'subquery_dependency';
  nodes: Array<TableSummaryNode | CteSummaryNode | SubquerySummaryNode | OutputGroupNode | OutputFieldNode | ExpressionGroupNode>;
  edges: Array<DependencySummaryEdge>;
  hiddenFieldEntityIds: string[];
  hiddenSemanticEdgeIds: string[];
  defaultOutputEntityIds: string[];
  diagnosticsSummary: DiagnosticsSummary;
}

// §14 OutputCapsule
export interface OutputCapsuleState {
  entity_id?: string;
  display_name?: string;
  status: 'empty' | 'chosen' | 'partial' | 'stale' | 'low_confidence';
  summary?: string;
}

// §19.1 DiagnosticAttention
export interface DiagnosticAttentionRule {
  diagnosticCode: string;
  defaultSeverity: 'info' | 'warning' | 'error';
  attentionLevel: 'L1' | 'L2' | 'L3' | 'L4';
  blocking: boolean;
  placement:
    | 'canvas_error_summary'
    | 'path_anchor'
    | 'detail_panel'
    | 'status_strip'
    | 'diagnostics_drawer'
    | 'editor_marker'
    | 'search_result_row';
  recommendedAction?:
    | 'locate_sql'
    | 'view_mapping'
    | 'reanalyze'
    | 'check_metadata'
    | 'switch_scope'
    | 'view_diagnostics';
}
