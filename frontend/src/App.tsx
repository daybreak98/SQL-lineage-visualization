import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { exampleSql, sourceLocations as mockSourceLocations, subqueryNodes } from './data/mockLineage';
import { transitionRenderMode } from './data/selectors';
import { analyzeSql, formatSql, getHealth, listMetadataTables } from './api/client';
import type { BackendAnalysisResult, BackendDiagnostic, Diagnostic, GraphEdge, GraphNode, SearchItem, SourceLocation, WorkbenchState } from './types/lineage';
import type { editor as monacoEditor } from 'monaco-editor';
import { revealInEditor } from './components/LineageCanvas/highlight';
import { TopBar } from './components/TopBar';
import { LeftNav } from './components/LeftNav';
import { SqlEditorPanel } from './components/SqlEditorPanel';
import { Splitter } from './components/Splitter';
import { SearchBar } from './components/SearchBar';
import { CanvasToolbar } from './components/CanvasToolbar';
import { LineageCanvas } from './components/LineageCanvas';
import { DetailPanel } from './components/DetailPanel';
import { StatusStrip } from './components/StatusStrip';
import { Drawer } from './components/Drawer';
import { MetadataDialog } from './components/MetadataDialog';

const initialState: WorkbenchState = {
  pageMode: 'analyzed',
  analysisStatus: 'success',
  trustStatus: 'trusted',
  selectedOutput: null,
  selectedEntity: 'out:group',
  selectedMapping: null,
  renderMode: 'subquery_dependency',
  graphViewMode: 'table',
  detailMode: 'compact',
  detailTab: 'summary',
  drawerOpen: false,
  drawerTab: 'diagnostics',
  split: 28,
  query: '',
  scope: 'all',
  large: false,
  // fallback: initial positions from mock subqueryNodes before any backend analysis
  positions: Object.fromEntries(subqueryNodes.map((n) => [n.id, { x: n.x, y: n.y }])),
  metadataLabel: 'metadata: loading',
  // fallback: initial source locations from mock before any backend analysis
  sourceLocations: mockSourceLocations,
};

function normalizeDiagnostic(diagnostic: BackendDiagnostic, index: number): Diagnostic {
  return {
    id: diagnostic.diagnostic_id || `backend-diag-${index}`,
    code: diagnostic.code,
    entityId: diagnostic.related_entity_ids?.[0] || 'out:group',
    severity: diagnostic.level,
    reason: diagnostic.message,
    impact: diagnostic.details ? JSON.stringify(diagnostic.details) : 'Backend diagnostic',
    action: diagnostic.suggestion || 'Review SQL, metadata, or parser diagnostics.',
  };
}

function normalizeEdgeType(type?: string): GraphEdge['type'] {
  if (type === 'projection') return 'projection';
  if (type === 'alias') return 'alias';
  if (type === 'unknown') return 'unknown';
  if (type === 'cte') return 'cte';
  if (type === 'subq' || type === 'subquery') return 'subq';
  if (type === 'expr' || type === 'expression') return 'expr';
  if (type === 'join') return 'join';
  if (type === 'output') return 'output';
  return 'table';
}

function analysisToGraph(result: BackendAnalysisResult): { graph: { nodes: GraphNode[]; edges: GraphEdge[] }; searchItems: SearchItem[]; colToTables: Record<string, string[]> } {
  const apiNodes = result.graph_view_model?.nodes || [];
  const apiEdges = result.graph_view_model?.edges || [];

  // ── Build table-level graph with Query Result node ──
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  let outputCols: string[] = [];
  let outputColEntities: { label: string; entityId: string }[] = [];
  let tableCol = 0;
  const colX = 420;
  const startY = 40;
  const rowH = 64;

  let colToTables: Record<string, string[]> = {};
  let maxLevel = 0;
    const baseX = 60;
    const levelGap = 200;

  if (apiNodes.length) {
    // Process backend graph_view_model: separate tables from outputs
    let outNode: GraphNode | null = null;
    apiNodes.forEach((node, i) => {
      const ntype = node.node_type || node.type || '';
      const label = node.label || node.name || '';
      const eid = node.entity_id || node.id || '';
      if (ntype === 'table' || ntype === 'cte' || ntype === 'subquery') {
        nodes.push({
          id: node.id || `api-node-${i}`,
          entityId: eid,
          type: ntype as GraphNode['type'],
          label: label.split('.').pop() || label,
          tag: ntype === 'cte' ? 'CTE' : ntype === 'subquery' ? 'SUBQ' : undefined,
          x: 60, y: startY + tableCol * rowH,
        });
        tableCol++;
      } else if (ntype === 'output_column') {
        outputCols.push(label);
        outputColEntities.push({ label, entityId: eid });
      }
    });

    // ── CTE 层级布局 ──
    // Build dependency graph: entityId → [dependent entityIds]
    const deps: Record<string, string[]> = {};
    apiEdges.forEach((edge) => {
      const src = edge.source || '';
      const tgt = edge.target || '';
      if (src && tgt) {
        deps[tgt] = deps[tgt] || [];
        deps[tgt].push(src);
      }
    });
    // BFS level assignment: physical tables = 0, CTE = max(source levels) + 1
    const levels: Record<string, number> = {};
    // Initialize physical tables
    nodes.forEach(n => {
      if (n.type === 'table') levels[n.entityId] = 0;
    });
    // Iterate until all CTE/subquery nodes get a level
    let changed = true;
    while (changed) {
      changed = false;
      nodes.forEach(n => {
        if (n.type !== 'cte' && n.type !== 'subquery') return;
        if (levels[n.entityId] !== undefined) return;
        const srcs = deps[n.entityId] || [];
        if (srcs.length === 0) {
          levels[n.entityId] = 1;
          changed = true;
        } else {
          const maxSrc = Math.max(...srcs.map(s => levels[s] ?? -1));
          if (maxSrc >= 0) {
            levels[n.entityId] = maxSrc + 1;
            changed = true;
          }
        }
      });
    }
    // Apply levels to positioning – 同层多节点按行号均匀分布，避免堆叠
    const yGap = 56;
    const levelRows: Record<number, number> = {};  // level → 当前行号
    nodes.forEach(n => {
      const lvl = levels[n.entityId] ?? 0;
      n.x = baseX + lvl * levelGap;
      const row = levelRows[lvl] || 0;
      n.y = startY + row * yGap;
      levelRows[lvl] = row + 1;
    });
    // Find max level for Query Result positioning
    maxLevel = Math.max(0, ...Object.values(levels));
    // Build mapping: output column entityId → source table entityIds (from edges)
    colToTables = {};
    // Collect all physical table entityIds for fallback
    const physicalTableIds = new Set<string>();
    apiNodes.forEach((node) => {
      if (node.node_type === 'table' || node.type === 'table') {
        physicalTableIds.add(node.entity_id || node.id || '');
      }
    });
    apiEdges.forEach((edge, ei) => {
      const src = edge.source || '';
      const tgt = edge.target || '';
      if (src && tgt) {
        colToTables[tgt] = colToTables[tgt] || [];
        // Check if the source directly references one of our physical tables
        let matched = false;
        for (const tid of physicalTableIds) {
          if (src.includes(tid.split(':').pop() || '')) {
            if (!colToTables[tgt].includes(tid)) colToTables[tgt].push(tid);
            matched = true;
          }
        }
        // Fallback: if source is a CTE column and no match, connect to all physical tables
        if (!matched && src.includes(':cte.')) {
          physicalTableIds.forEach(tid => {
            if (!colToTables[tgt].includes(tid)) colToTables[tgt].push(tid);
          });
        }
        edges.push({
          id: edge.id || `api-edge-${ei}`,
          source: src,
          target: tgt,
          type: normalizeEdgeType(edge.edge_type || edge.type),
          mapping: edge.mapping || edge.id,
        });
      }
    });
  } else {
    // Fallback: use tables_extracted
    const tables = result.tables_extracted || [];
    outputCols = result.columns_extracted || [];
    tables.forEach((table, index) => {
      nodes.push({ id: `api-table-${index}`, entityId: `table:${table}`, type: 'table', label: table.split('.').pop() || table, x: 60, y: startY + index * rowH });
    });
    tableCol = tables.length;
    // Redirect existing edges or create table→result edges
    tables.forEach((table, index) => {
      edges.push({ id: `api-table-edge-${index}`, source: `table:${table}`, target: 'out:query_result', type: 'table' });
    });
  }

  // Ensure all table-type nodes have an edge to Query Result
  const resultId = 'out:query_result';
  const tableNodes = nodes.filter(n => n.type === 'table' || n.type === 'cte' || n.type === 'subquery');

  // Add final Query Result node (positioned at max level + 1)
  const shortCols = outputColEntities.map(c => c.label.includes('.') ? c.label.split('.').pop()! : c.label);
  const resultLabel = shortCols.length > 0 ? `Query Result (${shortCols.length} cols)` : 'Query Result';
  // Place Query Result at avg Y of all table/CTE/subquery nodes
  const avgY = tableNodes.length > 0
    ? tableNodes.reduce((sum, n) => sum + n.y, 0) / tableNodes.length
    : startY;
  const resultX = baseX + (maxLevel + 1) * levelGap;
  nodes.push({ id: 'api-query-result', entityId: 'out:query_result', type: 'output', label: resultLabel, tag: 'OUT', x: resultX, y: avgY });

  tableNodes.forEach(tn => {
    if (!edges.some(e => e.source === tn.entityId && e.target === resultId)) {
      edges.push({ id: `edge-${tn.entityId}-result`, source: tn.entityId, target: resultId, type: 'table' });
    }
  });

  const searchItems: SearchItem[] = [
    { itemId: 'search-query-result', entityId: resultId, displayName: resultLabel, type: 'output', sub: `${tableNodes.length} tables · ${outputColEntities.length} cols`, reason: 'sql analyze', confidence: result.status === 'partial' ? 'medium' : 'high' },
    ...outputColEntities.map((col, i) => {
      const tables = colToTables[col.entityId];
      const hasSource = tables && tables.length > 0;
      return {
        itemId: `search-out-${i}`,
        entityId: col.entityId,
        displayName: col.label,
        type: 'output' as const,
        sub: hasSource ? `from: ${tables.join(', ')}` : 'unknown source',
        reason: hasSource ? `→ ${tables.join(', ')}` : '无法确认字段来源',
        confidence: hasSource ? ('high' as const) : ('low' as const),
        warning: !hasSource,
      };
    }),
    ...tableNodes.map(tn => ({ itemId: `search-${tn.entityId}`, entityId: tn.entityId, displayName: tn.label, type: 'source' as const, sub: tn.type, reason: 'backend', confidence: 'high' as const })),
  ];

  return { graph: { nodes, edges }, searchItems, colToTables };
}

function normalizeNodeType(type?: string): GraphNode['type'] {
  if (type === 'table') return 'table';
  if (type === 'column') return 'column';
  if (type === 'cte') return 'cte';
  if (type === 'subquery') return 'subquery';
  if (type === 'output_column' || type === 'output_field') return 'output_field';
  if (type === 'expression') return 'expression';
  if (type === 'unknown') return 'unknown';
  return 'output';
}

function tagForNodeType(type?: string) {
  if (type === 'output_column' || type === 'output_field') return 'OUT';
  if (type === 'column') return 'COL';
  if (type === 'table') return 'TBL';
  if (type === 'expression') return 'EXPR';
  if (type === 'unknown') return '?';
  return undefined;
}

export default function App() {
  const [sql, setSqlValue] = useState(exampleSql);
  const [dialect, setDialect] = useState('spark');
  const [activeNav, setActiveNav] = useState('workbench');
  const [state, setState] = useState<WorkbenchState>(initialState);
  const [metadataOpen, setMetadataOpen] = useState(false);

  // ── Bidirectional linking: Monaco ↔ Canvas ──
  const editorRef = useRef<monacoEditor.IStandaloneCodeEditor | null>(null);

  /** Called by SqlEditorPanel when Monaco editor mounts */
  const handleEditorMounted = useCallback((editor: monacoEditor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
  }, []);

  /** Called by LineageCanvas (double-click node) or DetailPanel (Locate SQL button) */
  const handleRevealInEditor = useCallback((entityId: string) => {
    revealInEditor(editorRef.current, entityId, state.sourceLocations, (id) => {
      // Graceful degradation: no SourceLocation found
      setState((s) => ({
        ...s,
        backendMessage: `No source location available for entity ${id}. Use the graph view to explore lineage.`,
      }));
    });
  }, [state.sourceLocations]);

  /** Called by SqlEditorPanel when cursor position matches a source location */
  const handleCursorEntityChange = useCallback((entityId: string | null) => {
    if (!entityId) return;
    setState((s) => {
      // Don't override if user explicitly selected something different
      if (s.selectedEntity === entityId) return s;
      return { ...s, selectedEntity: entityId };
    });
  }, []);

  const refreshMetadataLabel = useCallback(async () => {
    try {
      const [health, tables] = await Promise.all([getHealth(), listMetadataTables()]);
      setState((s) => ({ ...s, metadataLabel: `backend ${health.version} · metadata: ${tables.total} tables` }));
    } catch {
      setState((s) => ({ ...s, metadataLabel: 'metadata: backend offline' }));
    }
  }, []);

  useEffect(() => {
    void refreshMetadataLabel();
  }, [refreshMetadataLabel]);

  const setSql = (value: string) => {
    setSqlValue(value);
    setState((s) => {
      if (!value.trim()) return { ...s, pageMode: 'empty', analysisStatus: 'none', trustStatus: 'untrusted' };
      if (s.pageMode === 'analyzed' || s.trustStatus === 'trusted') return { ...s, pageMode: 'dirty', trustStatus: 'stale' };
      if (s.pageMode === 'empty') return { ...s, pageMode: 'ready', trustStatus: 'untrusted' };
      return s;
    });
  };

  const onTransition = useCallback((event: string) => {
    setState((s) => {
      const t = transitionRenderMode(s.renderMode, event);
      const patch: Partial<WorkbenchState> = { renderMode: t.mode, lastTransition: t.description };
      if (event === 'CLEAR_SELECTION') {
        patch.selectedOutput = null;
        patch.selectedEntity = 'out:group';
        patch.selectedMapping = null;
      }
      return { ...s, ...patch };
    });
  }, []);

  const onAnalyze = async () => {
    if (!sql.trim()) return;
    setState((s) => ({ ...s, pageMode: 'analyzing', analysisStatus: 'running', trustStatus: 'untrusted' }));
    try {
      const result = await analyzeSql(sql, dialect);
      const { graph, searchItems, colToTables } = analysisToGraph(result);
      const diagnostics = (result.diagnostics_report?.diagnostics || []).map(normalizeDiagnostic);
      setState((s) => {
        const failed = result.status === 'failed';
        const partial = result.status === 'partial';
        const t = transitionRenderMode(s.renderMode, failed ? 'ANALYZE_FAILED' : 'ANALYZE_SUCCESS');
        return {
          ...s,
          pageMode: failed ? 'failed' : 'analyzed',
          analysisStatus: failed ? 'failed' : partial ? 'partial' : 'success',
          trustStatus: failed ? 'untrusted' : 'trusted',
          selectedOutput: null,
          selectedEntity: 'out:group',
          selectedMapping: null,
          drawerOpen: s.drawerOpen,
          drawerTab: s.drawerTab,
          renderMode: t.mode,
          lastTransition: t.description,
          backendGraph: graph,
          backendSearchItems: searchItems,
          backendDiagnostics: diagnostics,
          colToTables: colToTables,
          backendMessage: `${result.analysis_id} · ${result.summary?.table_count ?? graph.nodes.length} nodes from backend`,
          positions: Object.fromEntries(graph.nodes.map((node) => [node.id, { x: node.x, y: node.y }])),
        };
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analyze request failed';
      setState((s) => {
        const t = transitionRenderMode(s.renderMode, 'ANALYZE_FAILED');
        return { ...s, pageMode: 'failed', analysisStatus: 'failed', trustStatus: 'untrusted', drawerOpen: s.drawerOpen, drawerTab: s.drawerTab, renderMode: t.mode, lastTransition: t.description, backendMessage: message, backendDiagnostics: [{ id: 'frontend-api-error', code: 'FRONTEND_API_ERROR', entityId: 'out:group', severity: 'error', reason: message, impact: 'The UI could not call /api/sql/analyze.', action: 'Start the backend service or inspect the API response.' }] };
      });
    }
  };

  const onSelectResult = (item: SearchItem) => {
    setState((s) => {
      // In table view, clicking an output column highlights its source table
      let targetEntity = item.entityId;
      if (item.type === 'output' && item.entityId !== 'out:query_result' && s.graphViewMode !== 'column') {
        const ct = s.colToTables?.[item.entityId];
        if (ct && ct.length > 0) {
          // Find the first source table node in backendGraph
          const graph = s.backendGraph;
          if (graph) {
            const tableNode = graph.nodes.find(n =>
              n.type === 'table' && ct.some(t => n.entityId.includes(t))
            );
            if (tableNode) targetEntity = tableNode.entityId;
          }
        }
      }
      const event = item.type === 'output' ? 'SELECT_OUTPUT_FIELD' : 'FOCUS_FIELD';
      const t = transitionRenderMode(s.renderMode, event);
      return {
        ...s,
        selectedOutput: item.type === 'output' ? item.entityId : s.selectedOutput,
        selectedEntity: targetEntity,
        selectedMapping: null,
        detailMode: 'compact',
        detailTab: 'summary',
        renderMode: t.mode,
        lastTransition: t.description,
      };
    });
  };

  const setSplit = (split: number) => setState((s) => ({ ...s, split }));

  const workspaceStyle = useMemo(() => ({ ['--split' as string]: `${state.split}%` }), [state.split]);

  return (
    <div className="app" style={workspaceStyle}>
      <TopBar
        state={state}
        dialect={dialect}
        setDialect={setDialect}
        onAnalyze={onAnalyze}
        onFormat={async () => {
          if (!sql.trim()) return;
          try {
            const response = await formatSql(sql, dialect);
            if (response.formatted_sql) {
              setSql(response.formatted_sql);
              setState((s) => ({ ...s, backendMessage: `formatted by /api/sql/format · ${response.dialect}` }));
            }
          } catch (err) {
            const message = err instanceof Error ? err.message : 'Format request failed';
            setState((s) => ({ ...s, backendMessage: message, drawerOpen: s.drawerOpen, drawerTab: s.drawerTab, backendDiagnostics: [{ id: 'format-api-error', code: 'FORMAT_API_ERROR', entityId: 'out:group', severity: 'error', reason: message, impact: 'The UI could not call /api/sql/format.', action: 'Start the backend service or inspect the format endpoint.' }] }));
          }
        }}
        onLoadExample={() => {
          setSqlValue(exampleSql);
          setState((s) => ({ ...s, pageMode: 'ready', analysisStatus: 'none', trustStatus: 'untrusted' }));
        }}
        onMetadata={() => setMetadataOpen(true)}
        onMore={() => setState((s) => ({ ...s, drawerOpen: !s.drawerOpen, drawerTab: 'more' }))}
      />
      <div className="body">
        <LeftNav active={activeNav} onOpen={(tab) => { setActiveNav(tab); if (tab !== 'workbench') setState((s) => ({ ...s, drawerOpen: true, drawerTab: tab })); }} />
        <main className="app-main">
          <div className="workspace" id="workspace">
            <SqlEditorPanel sql={sql} setSql={setSql} state={state} dialect={dialect} sourceLocations={state.sourceLocations} onEditorMounted={handleEditorMounted} onCursorEntityChange={handleCursorEntityChange} />
            <Splitter split={state.split} setSplit={setSplit} />
            <section className="canvas-panel">
              <SearchBar state={state} setState={setState} onSelectResult={onSelectResult} />
              <CanvasToolbar state={state} setState={setState} onTransition={onTransition} />
              <LineageCanvas state={state} setState={setState} onNodeDoubleClick={handleRevealInEditor} />
              <DetailPanel state={state} setState={setState} onLocateSql={handleRevealInEditor} />
            </section>
          </div>
          <StatusStrip state={state} setState={setState} />
          <Drawer state={state} setState={setState} />
        </main>
      </div>
      <MetadataDialog open={metadataOpen} onClose={() => setMetadataOpen(false)} onImported={refreshMetadataLabel} />
    </div>
  );
}
