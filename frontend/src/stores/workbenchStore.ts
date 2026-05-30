import { create } from 'zustand';
import type {
  PageMode,
  AnalysisStatus,
  TrustStatus,
  WorkbenchRuntimeState,
} from '../types/state';
import type { PathContextStore } from '../types/path';
import type {
  GraphRenderMode,
  SubqueryDependencyViewModel,
} from '../types/graph';
import type { AttentionViewModel } from '../types/attention';

// ---- §4.2 状态映射: derivePageMode ----
function derivePageMode(
  sql: string,
  analysisStatus: AnalysisStatus,
  sqlChangedSinceAnalysis: boolean,
): PageMode {
  if (!sql.trim()) return 'empty';
  if (analysisStatus === 'none') return 'ready';
  if (analysisStatus === 'running') return 'analyzing';
  if (analysisStatus === 'failed') return 'failed';
  // success / partial / timeout 但有部分结果
  if (sqlChangedSinceAnalysis) return 'dirty';
  return 'analyzed';
}

// ---- §4.2 状态映射: deriveTrustStatus ----
function deriveTrustStatus(
  analysisStatus: AnalysisStatus,
  sqlChangedSinceAnalysis: boolean,
): TrustStatus {
  if (analysisStatus === 'none' || analysisStatus === 'failed') return 'untrusted';
  if (sqlChangedSinceAnalysis) return 'stale';
  return 'trusted';
}

// ---- §4.3 硬规则：sqlChangeDetected ----
function sqlChangeDetected(
  sql: string,
  lastTrustedSqlHash: string | undefined,
): boolean {
  if (!lastTrustedSqlHash) return false;
  // 简单哈希比对（P0 阶段用长度+内容摘要，后续可替换为完整 hash）
  const currentHash = simpleHash(sql);
  return currentHash !== lastTrustedSqlHash;
}

function simpleHash(s: string): string {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    const chr = s.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0;
  }
  return hash.toString(36);
}

// ---- §5.3 派生规则: deriveAttention ----
function deriveAttention(
  pageMode: PageMode,
  selectedOutputEntityId: string | undefined,
  selectedEntityId: string | undefined,
  selectedEdgeMappingId: string | undefined,
  detailPanelOpen: boolean,
  locatingSql: boolean,
): AttentionViewModel {
  let primaryFocus: AttentionViewModel['primaryFocus'];
  let taskStage: AttentionViewModel['taskStage'];
  let source: AttentionViewModel['source'];

  if (pageMode === 'empty') {
    primaryFocus = 'empty_guide';
    taskStage = 'empty';
    source = 'page_mode';
  } else if (pageMode === 'ready') {
    primaryFocus = 'analyze';
    taskStage = 'ready';
    source = 'page_mode';
  } else if (pageMode === 'analyzing') {
    primaryFocus = 'analyze';
    taskStage = 'analyzing';
    source = 'page_mode';
  } else if (pageMode === 'failed') {
    primaryFocus = 'error_summary';
    taskStage = 'failed';
    source = 'diagnostic';
  } else if (pageMode === 'dirty') {
    primaryFocus = 're_analyze';
    taskStage = 'dirty';
    source = 'editor_dirty';
  } else {
    // pageMode === 'analyzed'
    if (locatingSql) {
      primaryFocus = 'monaco_range';
      taskStage = 'locating_sql';
      source = 'selection';
    } else if (selectedEdgeMappingId) {
      primaryFocus = 'detail_mapping';
      taskStage = 'object_selected';
      source = 'selection';
    } else if (selectedEntityId && detailPanelOpen) {
      primaryFocus = 'detail_mapping';
      taskStage = 'object_selected';
      source = 'selection';
    } else if (selectedOutputEntityId) {
      primaryFocus = 'current_path';
      taskStage = 'path_selected';
      source = 'path_context';
    } else {
      primaryFocus = 'search_default_output';
      taskStage = 'analyzed_no_field';
      source = 'page_mode';
    }
  }

  return {
    primaryFocus,
    taskStage,
    reason: `derived from pageMode=${pageMode} source=${source}`,
    source,
  };
}

// ---- §7.3 迁移规则: GraphRenderMode 状态机 ----
type RenderModeEvent =
  | 'ANALYZE_SUCCESS'
  | 'SELECT_OUTPUT_FIELD'
  | 'FOCUS_FIELD'
  | 'OPEN_SEMANTIC_MODE'
  | 'ENTER_LARGE_GRAPH'
  | 'OPEN_FULL_PREVIEW'
  | 'CLEAR_SELECTION'
  | 'REANALYZE'
  | 'ANALYZE_FAILED';

function transitionRenderMode(
  currentMode: GraphRenderMode,
  event: RenderModeEvent,
): { to: GraphRenderMode; preserveViewport: boolean; recomputeLayout: boolean } {
  const transitions: Record<GraphRenderMode, Partial<Record<RenderModeEvent, { to: GraphRenderMode; preserveViewport: boolean; recomputeLayout: boolean }>>> = {
    subquery_dependency: {
      ANALYZE_SUCCESS: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: true },
      SELECT_OUTPUT_FIELD: { to: 'current_field_path', preserveViewport: false, recomputeLayout: false },
      ENTER_LARGE_GRAPH: { to: 'large_graph', preserveViewport: true, recomputeLayout: false },
      OPEN_FULL_PREVIEW: { to: 'full_graph_preview', preserveViewport: false, recomputeLayout: true },
      ANALYZE_FAILED: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
    },
    current_field_path: {
      FOCUS_FIELD: { to: 'focus_field', preserveViewport: true, recomputeLayout: false },
      OPEN_SEMANTIC_MODE: { to: 'semantic_mode', preserveViewport: true, recomputeLayout: false },
      CLEAR_SELECTION: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
      ENTER_LARGE_GRAPH: { to: 'large_graph', preserveViewport: true, recomputeLayout: false },
      OPEN_FULL_PREVIEW: { to: 'full_graph_preview', preserveViewport: false, recomputeLayout: true },
      ANALYZE_FAILED: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
    },
    focus_field: {
      CLEAR_SELECTION: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
      ENTER_LARGE_GRAPH: { to: 'large_graph', preserveViewport: true, recomputeLayout: false },
      OPEN_FULL_PREVIEW: { to: 'full_graph_preview', preserveViewport: false, recomputeLayout: true },
      ANALYZE_FAILED: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
    },
    semantic_mode: {
      CLEAR_SELECTION: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
      ENTER_LARGE_GRAPH: { to: 'large_graph', preserveViewport: true, recomputeLayout: false },
      OPEN_FULL_PREVIEW: { to: 'full_graph_preview', preserveViewport: false, recomputeLayout: true },
      ANALYZE_FAILED: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
    },
    large_graph: {
      CLEAR_SELECTION: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
      ANALYZE_SUCCESS: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: true },
      ANALYZE_FAILED: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
    },
    full_graph_preview: {
      CLEAR_SELECTION: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
      ANALYZE_SUCCESS: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: true },
      ANALYZE_FAILED: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
    },
  };

  // 跨状态的全局事件（§7.3 迁移规则表）
  const globalTransitions: Partial<Record<RenderModeEvent, { to: GraphRenderMode; preserveViewport: boolean; recomputeLayout: boolean }>> = {
    ANALYZE_SUCCESS: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: true },
    REANALYZE: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: true },
    ANALYZE_FAILED: { to: 'subquery_dependency', preserveViewport: false, recomputeLayout: false },
  };

  const specific = transitions[currentMode]?.[event];
  if (specific) return specific;

  const global = globalTransitions[event];
  if (global) return global;

  // 默认不迁移
  return { to: currentMode, preserveViewport: true, recomputeLayout: false };
}

// ================================================================
// WorkbenchStore
// ================================================================

interface WorkbenchStore extends WorkbenchRuntimeState, PathContextStore {
  // Editor state
  sql: string;
  dialect: string;
  defaultCatalog: string;
  defaultSchema: string;

  // Graph state
  renderMode: GraphRenderMode;
  selectedEntityId?: string;
  selectedEdgeMappingId?: string;

  // UI
  detailPanelOpen: boolean;

  // Resolved graph view model (set after ANALYSIS_SUCCESS)
  subqueryDependencyViewModel?: SubqueryDependencyViewModel;

  // Derived (computed via selectors, not stored)
  // attention: AttentionViewModel -- derived

  // Actions
  setSql: (sql: string) => void;
  setDialect: (d: string) => void;
  requestAnalyze: () => Promise<void>;
  selectOutputField: (entityId: string, displayName: string) => void;
  selectEntity: (entityId: string | null) => void;
  selectEdgeMapping: (mappingId: string | null) => void;
  clearSelection: () => void;
  openDetailPanel: () => void;
  closeDetailPanel: () => void;
  setRenderMode: (mode: GraphRenderMode) => void;
  dispatchRenderEvent: (event: RenderModeEvent) => void;
}

// ---- SELECTORS ----

/** §5.3 派生注意力模型 */
export function selectAttention(state: WorkbenchStore): AttentionViewModel {
  return deriveAttention(
    state.pageMode,
    state.selectedOutputEntityId,
    state.selectedEntityId,
    state.selectedEdgeMappingId,
    state.detailPanelOpen,
    false,
  );
}

/** §7.3 当前 renderMode 是否允许选择输出字段 */
export function selectCanSelectOutput(state: WorkbenchStore): boolean {
  return state.pageMode === 'analyzed' && state.trustStatus !== 'stale';
}

/** §14 输出胶囊状态 */
export function selectOutputCapsule(state: WorkbenchStore): {
  entity_id?: string;
  display_name?: string;
  status: 'empty' | 'chosen' | 'partial' | 'stale' | 'low_confidence';
  summary?: string;
} {
  if (!state.selectedOutputEntityId) {
    return { status: 'empty' };
  }
  if (state.trustStatus === 'stale' || state.pathStatus === 'stale') {
    return {
      entity_id: state.selectedOutputEntityId,
      display_name: state.selectedOutputDisplayName,
      status: 'stale',
      summary: 'SQL changed · Re-analyze required',
    };
  }
  if (state.pathStatus === 'partial') {
    return {
      entity_id: state.selectedOutputEntityId,
      display_name: state.selectedOutputDisplayName,
      status: 'partial',
      summary: `Partial lineage · ${state.unresolvedCount ?? 0} unresolved mappings`,
    };
  }
  if (state.pathStatus === 'low_confidence' || state.confidenceLevel === 'low') {
    return {
      entity_id: state.selectedOutputEntityId,
      display_name: state.selectedOutputDisplayName,
      status: 'low_confidence',
      summary: 'Source uncertain · verify mapping',
    };
  }
  return {
    entity_id: state.selectedOutputEntityId,
    display_name: state.selectedOutputDisplayName,
    status: 'chosen',
  };
}

// ---- STORE ----

export const useWorkbenchStore = create<WorkbenchStore>((set, get) => ({
  // ---- WorkbenchRuntimeState 初始值 ----
  pageMode: 'empty',
  analysisStatus: 'none',
  trustStatus: 'untrusted',
  analysisId: undefined,
  sqlHash: undefined,
  metadataVersion: undefined,
  staleReason: undefined,
  lastTrustedAnalysisId: undefined,
  lastTrustedSqlHash: undefined,

  // ---- PathContextStore 初始值 ----
  selectedOutputEntityId: undefined,
  selectedOutputDisplayName: undefined,
  pathMode: 'none',
  pathStatus: 'idle',
  pathRef: undefined,
  nodeCount: undefined,
  mappingCount: undefined,
  warningCount: undefined,
  unresolvedCount: undefined,
  confidenceLevel: undefined,
  // staleReason reuses WorkbenchRuntimeState.staleReason

  // ---- Editor state ----
  sql: '',
  dialect: 'mysql',
  defaultCatalog: '',
  defaultSchema: '',

  // ---- Graph state ----
  renderMode: 'subquery_dependency',
  selectedEntityId: undefined,
  selectedEdgeMappingId: undefined,

  // ---- UI ----
  detailPanelOpen: false,

  subqueryDependencyViewModel: undefined,

  // ---- Actions ----

  setSql: (sql: string) => {
    const state = get();
    const changed = sqlChangeDetected(sql, state.lastTrustedSqlHash);

    // §4.3 硬规则 1：SQL 文本变化后，pageMode 必须变为 dirty
    if (changed && state.pageMode === 'analyzed') {
      set({
        sql,
        pageMode: 'dirty',
        trustStatus: 'stale',
        staleReason: 'sql_changed',
        sqlHash: simpleHash(sql),
        selectedOutputEntityId: undefined,
        selectedOutputDisplayName: undefined,
        pathMode: 'none',
        pathStatus: 'stale',
      });
    } else {
      const newPageMode = derivePageMode(
        sql,
        state.analysisStatus,
        changed,
      );
      const newTrust = deriveTrustStatus(state.analysisStatus, changed);
      set({
        sql,
        pageMode: newPageMode,
        trustStatus: newTrust,
        sqlHash: simpleHash(sql),
        staleReason: changed ? 'sql_changed' : undefined,
      });
    }
  },

  setDialect: (d: string) => set({ dialect: d }),

  requestAnalyze: async () => {
    const state = get();
    if (!state.sql.trim()) return;

    // §4.2: 分析中
    set({
      analysisStatus: 'running',
      pageMode: 'analyzing',
      trustStatus: 'untrusted',
    });

    try {
      const response = await fetch('/api/sql/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sql: state.sql,
          dialect: state.dialect,
          default_catalog: state.defaultCatalog,
          default_schema: state.defaultSchema,
        }),
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.status}`);
      }

      const data = await response.json();
      // data 包含 analysis_id, graph_view_model, diagnostics, etc.
      const analysisId: string = data.analysis_id;
      const currentSqlHash = simpleHash(state.sql);

      // §7.3: ANALYZE_SUCCESS → subquery_dependency
      const result = transitionRenderMode(state.renderMode, 'ANALYZE_SUCCESS');

      set({
        analysisStatus: data.status === 'partial' ? 'partial' : 'success',
        pageMode: 'analyzed',
        trustStatus: 'trusted',
        analysisId,
        sqlHash: currentSqlHash,
        metadataVersion: data.metadata_version,
        lastTrustedAnalysisId: analysisId,
        lastTrustedSqlHash: currentSqlHash,
        renderMode: result.to,
        // PathContext 重置
        selectedOutputEntityId: undefined,
        selectedOutputDisplayName: undefined,
        pathMode: 'none',
        pathStatus: 'idle',
        // Resolved view model from backend
        subqueryDependencyViewModel: data.subquery_dependency_view,
      });
    } catch (err) {
      // §7.3: ANALYZE_FAILED → subquery_dependency
      const result = transitionRenderMode(state.renderMode, 'ANALYZE_FAILED');
      set({
        analysisStatus: 'failed',
        pageMode: 'failed',
        trustStatus: 'untrusted',
        renderMode: result.to,
      });
    }
  },

  selectOutputField: (entityId: string, displayName: string) => {
    const state = get();
    if (!selectCanSelectOutput(state)) return;

    // §7.3: SELECT_OUTPUT_FIELD → current_field_path
    const result = transitionRenderMode(state.renderMode, 'SELECT_OUTPUT_FIELD');

    // §6.1 单源原则：PathContextStore 是唯一事实源
    set({
      selectedOutputEntityId: entityId,
      selectedOutputDisplayName: displayName,
      pathMode: 'upstream',
      pathStatus: 'ready',
      renderMode: result.to,
    });

    // TODO M5: 调用 FieldPathApi 获取 pathRef, nodeCount, mappingCount 等
  },

  selectEntity: (entityId: string | null) => {
    set({
      selectedEntityId: entityId ?? undefined,
      selectedEdgeMappingId: undefined,
      detailPanelOpen: entityId !== null,
    });
  },

  selectEdgeMapping: (mappingId: string | null) => {
    set({
      selectedEdgeMappingId: mappingId ?? undefined,
      selectedEntityId: undefined,
      detailPanelOpen: mappingId !== null,
    });
  },

  clearSelection: () => {
    const state = get();
    // §7.3: CLEAR_SELECTION → subquery_dependency
    const result = transitionRenderMode(state.renderMode, 'CLEAR_SELECTION');
    set({
      selectedEntityId: undefined,
      selectedEdgeMappingId: undefined,
      detailPanelOpen: false,
      renderMode: result.to,
      // 保留 selectedOutputEntityId（不清除输出字段选择）
    });
  },

  openDetailPanel: () => set({ detailPanelOpen: true }),
  closeDetailPanel: () => set({ detailPanelOpen: false }),

  setRenderMode: (mode: GraphRenderMode) => set({ renderMode: mode }),

  dispatchRenderEvent: (event: RenderModeEvent) => {
    const state = get();
    const result = transitionRenderMode(state.renderMode, event);
    set({ renderMode: result.to });
  },
}));

export type { RenderModeEvent };
