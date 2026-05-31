import { useCallback, useEffect, useMemo, useState } from 'react';
import { exampleSql, subqueryNodes } from './data/mockLineage';
import { transitionRenderMode } from './data/selectors';
import { analyzeSql, formatSql, getHealth, listMetadataTables } from './api/client';
import type { BackendAnalysisResult, BackendDiagnostic, Diagnostic, GraphEdge, GraphNode, SearchItem, WorkbenchState } from './types/lineage';
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
  detailMode: 'compact',
  detailTab: 'summary',
  drawerOpen: false,
  drawerTab: 'diagnostics',
  split: 44,
  query: '',
  scope: 'all',
  large: false,
  positions: Object.fromEntries(subqueryNodes.map((n) => [n.id, { x: n.x, y: n.y }])),
  metadataLabel: 'metadata: loading',
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

function analysisToGraph(result: BackendAnalysisResult): { graph: { nodes: GraphNode[]; edges: GraphEdge[] }; searchItems: SearchItem[] } {
  const apiNodes = result.graph_view_model?.nodes || [];
  if (apiNodes.length) {
    const nodes: GraphNode[] = apiNodes.map((node, index) => ({
      id: node.id || `api-node-${index}`,
      entityId: node.entity_id || node.id || `api-node-${index}`,
      type: normalizeNodeType(node.node_type || node.type),
      label: node.label || node.name || node.entity_id || node.id || `node_${index}`,
      tag: tagForNodeType(node.node_type || node.type),
      x: node.position?.x ?? node.x ?? 60 + index * 180,
      y: node.position?.y ?? node.y ?? 80 + (index % 5) * 54,
    }));
    const edges: GraphEdge[] = (result.graph_view_model?.edges || []).map((edge, index) => ({
      id: edge.id || `api-edge-${index}`,
      source: edge.source || '',
      target: edge.target || '',
      type: normalizeEdgeType(edge.edge_type || edge.type),
      mapping: edge.mapping || edge.id,
    })).filter((edge) => edge.source && edge.target);
    return {
      graph: { nodes, edges },
      searchItems: nodes.map((node) => ({
        itemId: node.id,
        entityId: node.entityId,
        displayName: node.label,
        type: node.type === 'table' || node.type === 'column' ? 'source' : node.type === 'expression' ? 'expression' : node.type === 'unknown' ? 'diagnostic' : 'output',
        sub: node.type,
        reason: 'backend AnalysisResult',
        confidence: result.confidence_level === 'low' ? 'low' : result.status === 'partial' ? 'medium' : 'high',
        warning: node.type === 'unknown',
      })),
    };
  }

  const tables = result.tables_extracted || [];
  const columns = result.columns_extracted || [];
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  tables.forEach((table, index) => {
    nodes.push({ id: `api-table-${index}`, entityId: `table:${table}`, type: 'table', label: table.split('.').pop() || table, x: 40, y: 72 + index * 58 });
  });
  nodes.push({ id: 'api-parse', entityId: 'parse:main', type: 'cte', label: 'SQL Parse', tag: 'API', x: 300, y: 100 + Math.max(0, tables.length - 1) * 24 });
  tables.forEach((table, index) => edges.push({ id: `api-table-edge-${index}`, source: `table:${table}`, target: 'parse:main', type: 'table' }));
  columns.forEach((column, index) => {
    const entityId = `out:${column}`;
    nodes.push({ id: `api-column-${index}`, entityId, type: 'output_field', label: column.split('.').pop() || column, tag: 'OUT', x: 570, y: 52 + index * 52 });
    edges.push({ id: `api-output-edge-${index}`, source: 'parse:main', target: entityId, type: 'output' });
  });
  if (!columns.length && tables.length) {
    nodes.push({ id: 'api-output-placeholder', entityId: 'out:parse_result', type: 'output', label: 'parse_result', tag: 'OUT', x: 570, y: 104 });
    edges.push({ id: 'api-output-placeholder-edge', source: 'parse:main', target: 'out:parse_result', type: 'output' });
  }
  const searchItems: SearchItem[] = [
    ...columns.map((column, index) => ({ itemId: `api-column-${index}`, entityId: `out:${column}`, displayName: column, type: 'output' as const, sub: 'backend column', reason: 'sql analyze', confidence: 'high' as const })),
    ...tables.map((table, index) => ({ itemId: `api-table-${index}`, entityId: `table:${table}`, displayName: table, type: 'source' as const, sub: 'backend table', reason: 'sql analyze', confidence: 'high' as const })),
  ];
  return { graph: { nodes, edges }, searchItems };
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
  const [dialect, setDialect] = useState('Hive');
  const [activeNav, setActiveNav] = useState('workbench');
  const [state, setState] = useState<WorkbenchState>(initialState);
  const [metadataOpen, setMetadataOpen] = useState(false);

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
      const { graph, searchItems } = analysisToGraph(result);
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
          drawerOpen: failed || partial || diagnostics.length > 0 ? true : s.drawerOpen,
          drawerTab: failed || partial || diagnostics.length > 0 ? 'diagnostics' : s.drawerTab,
          renderMode: t.mode,
          lastTransition: t.description,
          backendGraph: graph,
          backendSearchItems: searchItems,
          backendDiagnostics: diagnostics,
          backendMessage: `${result.analysis_id} · ${result.summary?.table_count ?? graph.nodes.length} nodes from backend`,
          positions: Object.fromEntries(graph.nodes.map((node) => [node.id, { x: node.x, y: node.y }])),
        };
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analyze request failed';
      setState((s) => {
        const t = transitionRenderMode(s.renderMode, 'ANALYZE_FAILED');
        return { ...s, pageMode: 'failed', analysisStatus: 'failed', trustStatus: 'untrusted', drawerOpen: true, drawerTab: 'diagnostics', renderMode: t.mode, lastTransition: t.description, backendMessage: message, backendDiagnostics: [{ id: 'frontend-api-error', code: 'FRONTEND_API_ERROR', entityId: 'out:group', severity: 'error', reason: message, impact: 'The UI could not call /api/sql/analyze.', action: 'Start the backend service or inspect the API response.' }] };
      });
    }
  };

  const onSelectResult = (item: SearchItem) => {
    setState((s) => {
      const event = item.type === 'output' ? 'SELECT_OUTPUT_FIELD' : 'FOCUS_FIELD';
      const t = transitionRenderMode(s.renderMode, event);
      return {
        ...s,
        selectedOutput: item.type === 'output' ? item.entityId : s.selectedOutput,
        selectedEntity: item.entityId,
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
            setState((s) => ({ ...s, backendMessage: message, drawerOpen: true, drawerTab: 'diagnostics', backendDiagnostics: [{ id: 'format-api-error', code: 'FORMAT_API_ERROR', entityId: 'out:group', severity: 'error', reason: message, impact: 'The UI could not call /api/sql/format.', action: 'Start the backend service or inspect the format endpoint.' }] }));
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
        <main className="main">
          <div className="workspace" id="workspace">
            <SqlEditorPanel sql={sql} setSql={setSql} state={state} dialect={dialect} />
            <Splitter split={state.split} setSplit={setSplit} />
            <section className="canvas-panel">
              <SearchBar state={state} setState={setState} onSelectResult={onSelectResult} />
              <CanvasToolbar state={state} setState={setState} onTransition={onTransition} />
              <LineageCanvas state={state} setState={setState} />
              <DetailPanel state={state} setState={setState} />
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
