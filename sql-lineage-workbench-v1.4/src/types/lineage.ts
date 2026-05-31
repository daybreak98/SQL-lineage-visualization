export type PageMode = 'empty' | 'ready' | 'analyzing' | 'analyzed' | 'dirty' | 'failed';
export type AnalysisStatus = 'none' | 'running' | 'success' | 'partial' | 'failed';
export type TrustStatus = 'trusted' | 'stale' | 'untrusted';
export type GraphRenderMode = 'subquery_dependency' | 'current_field_path' | 'focus_field' | 'semantic_mode' | 'large_graph' | 'full_graph_preview';
export type DetailTab = 'summary' | 'mapping' | 'source' | 'diagnostics' | 'semantics';
export type DetailMode = 'collapsed' | 'compact' | 'expanded';

export interface Entity {
  id: string;
  type: 'table' | 'cte' | 'subquery' | 'output_group' | 'output_field' | 'column' | 'expression' | 'unknown' | 'join';
  name: string;
  comment: string;
}

export interface SourceLocation {
  entityId: string;
  line: number;
  col: number;
  rangeType: 'exact' | 'approximate' | 'unavailable';
  raw: string;
}

export interface Diagnostic {
  id: string;
  code: string;
  entityId: string;
  severity: 'info' | 'warning' | 'error';
  reason: string;
  impact: string;
  action: string;
}

export interface EdgeMapping {
  id: string;
  source: string;
  target: string;
  expression?: string;
  relation: 'direct' | 'aggregate' | 'expression' | 'join_dependency';
  confidence: 'high' | 'medium' | 'low';
}

export interface SearchItem {
  itemId: string;
  entityId: string;
  displayName: string;
  type: 'output' | 'source' | 'subquery' | 'expression' | 'diagnostic';
  sub: string;
  reason: string;
  confidence: 'high' | 'medium' | 'low';
  warning?: boolean;
}

export interface GraphNode {
  id: string;
  entityId: string;
  type: 'table' | 'cte' | 'subquery' | 'output' | 'output_field' | 'expression' | 'unknown';
  label: string;
  tag?: string;
  x: number;
  y: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: 'table' | 'cte' | 'subq' | 'output' | 'expr' | 'join';
  mapping?: string;
}

export interface PathContext {
  status: 'idle' | 'ready' | 'partial' | 'stale' | 'low_confidence';
  display: string;
  nodes: number;
  mappings: number;
  warnings: number;
  confidence: 'high' | 'medium' | 'unknown';
}

export interface WorkbenchState {
  pageMode: PageMode;
  analysisStatus: AnalysisStatus;
  trustStatus: TrustStatus;
  selectedOutput: string | null;
  selectedEntity: string;
  selectedMapping: string | null;
  renderMode: GraphRenderMode;
  detailMode: DetailMode;
  detailTab: DetailTab;
  drawerOpen: boolean;
  drawerTab: string;
  split: number;
  query: string;
  scope: string;
  large: boolean;
  lastTransition?: string;
  positions: Record<string, { x: number; y: number }>;
}
