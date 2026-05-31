import { useCallback, useMemo, useState } from 'react';
import { exampleSql, subqueryNodes } from './data/mockLineage';
import { transitionRenderMode } from './data/selectors';
import type { SearchItem, WorkbenchState } from './types/lineage';
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
};

export default function App() {
  const [sql, setSqlValue] = useState(exampleSql);
  const [dialect, setDialect] = useState('Hive');
  const [activeNav, setActiveNav] = useState('workbench');
  const [state, setState] = useState<WorkbenchState>(initialState);

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

  const onAnalyze = () => {
    if (!sql.trim()) return;
    setState((s) => ({ ...s, pageMode: 'analyzing', analysisStatus: 'running', trustStatus: 'untrusted' }));
    window.setTimeout(() => {
      setState((s) => {
        const lower = sql.toLowerCase();
        const t = transitionRenderMode(s.renderMode, lower.includes('broken_parse') ? 'ANALYZE_FAILED' : 'ANALYZE_SUCCESS');
        if (lower.includes('broken_parse')) {
          return { ...s, pageMode: 'failed', analysisStatus: 'failed', trustStatus: 'untrusted', selectedOutput: null, selectedEntity: 'out:group', drawerOpen: true, drawerTab: 'diagnostics', renderMode: t.mode, lastTransition: t.description };
        }
        if (lower.includes('unknown_col') || lower.includes('lateral view')) {
          return { ...s, pageMode: 'analyzed', analysisStatus: 'partial', trustStatus: 'trusted', selectedOutput: null, selectedEntity: 'out:group', drawerOpen: true, drawerTab: 'diagnostics', renderMode: t.mode, lastTransition: t.description };
        }
        return { ...s, pageMode: 'analyzed', analysisStatus: 'success', trustStatus: 'trusted', selectedOutput: null, selectedEntity: 'out:group', selectedMapping: null, renderMode: t.mode, lastTransition: t.description };
      });
    }, 420);
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
        onFormat={() => {
          setSql(sql.replace(/\bSELECT\b/g, 'select').replace(/\bFROM\b/g, 'from').replace(/\bWHERE\b/g, 'where'));
        }}
        onLoadExample={() => {
          setSqlValue(exampleSql);
          setState((s) => ({ ...s, pageMode: 'ready', analysisStatus: 'none', trustStatus: 'untrusted' }));
        }}
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
    </div>
  );
}
