import { deriveAttention } from '../data/selectors';
import type { WorkbenchState } from '../types/lineage';
import { cx } from '../utils/cx';

interface Props {
  state: WorkbenchState;
  dialect: string;
  setDialect: (value: string) => void;
  onAnalyze: () => void;
  onFormat: () => void;
  onLoadExample: () => void;
  onMore: () => void;
}

function statusClass(state: WorkbenchState) {
  if (state.pageMode === 'failed') return 'failed';
  if (state.pageMode === 'analyzing') return 'running';
  if (state.analysisStatus === 'partial') return 'partial';
  if (state.trustStatus === 'trusted') return 'trusted';
  if (state.trustStatus === 'stale') return 'stale';
  return '';
}

export function TopBar({ state, dialect, setDialect, onAnalyze, onFormat, onLoadExample, onMore }: Props) {
  const [focus, , source] = deriveAttention(state);
  const primaryLabel = state.pageMode === 'analyzing' ? 'Cancel' : state.pageMode === 'dirty' ? 'Re-analyze' : state.pageMode === 'failed' ? 'Fix SQL' : 'Analyze';
  const secondary = state.pageMode === 'analyzed' && state.trustStatus === 'trusted';
  return (
    <div className="topbar">
      <div className="brand">
        <div className="logo">SQL</div>
        <div>
          <div className="title">SQL Lineage</div>
          <div className="sub">v1.4 merged final · Subquery first · P0-Core</div>
        </div>
        <select className="select" value={dialect} onChange={(event) => setDialect(event.target.value)}>
          <option>Hive</option>
          <option>Spark</option>
          <option>Generic</option>
        </select>
        <span className="badge">metadata: intl_hotel_v20260527</span>
      </div>
      <div className="actions">
        <button className="btn optional" onClick={onLoadExample}>Load Example</button>
        <button className="btn" onClick={onFormat}>Format</button>
        <button className={cx('btn-primary', secondary && 'secondary')} onClick={onAnalyze}>{primaryLabel}</button>
        <button className="btn" onClick={onMore}>More</button>
        <span className={cx('pill', statusClass(state))}>{state.pageMode} · {state.analysisStatus} · {state.trustStatus}</span>
        <span className={cx('pill', focus === 'error_summary' ? 'failed' : focus === 're_analyze' ? 'stale' : focus === 'current_path' ? 'trusted' : '')}>{focus} · {source}</span>
      </div>
    </div>
  );
}
