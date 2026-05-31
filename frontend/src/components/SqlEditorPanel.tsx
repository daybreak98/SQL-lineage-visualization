import { sourceLocations } from '../data/mockLineage';
import type { WorkbenchState } from '../types/lineage';
import { cx } from '../utils/cx';

interface Props {
  sql: string;
  setSql: (value: string) => void;
  state: WorkbenchState;
  dialect: string;
}

export function SqlEditorPanel({ sql, setSql, state, dialect }: Props) {
  const lines = sql.split('\n');
  const loc = sourceLocations[state.selectedEntity];
  const canReveal = state.pageMode === 'analyzed' && state.trustStatus === 'trusted' && loc;
  return (
    <section className="editor">
      <div className="panel-head">
        <div><b>Monaco SqlEditor</b><span className="badge">Adapter Shell</span><span className="badge">{state.trustStatus}</span></div>
        <span>Ctrl/Cmd + Enter</span>
      </div>
      <div className="editor-body">
        {canReveal && <div className={cx('highlight block', loc.rangeType === 'approximate' && 'weak')} style={{ top: 12 + (loc.line - 1) * 22 }} />}
        <div className="line-numbers">
          {lines.map((_, index) => <div key={index} className={canReveal && loc.line === index + 1 ? 'active' : ''}>{index + 1}</div>)}
        </div>
        <textarea id="sqlEditor" spellCheck={false} value={sql} onChange={(event) => setSql(event.target.value)} />
      </div>
      <div className="editor-foot">
        <span>Ln {lines.length}, Col 1 · {dialect} · pageMode={state.pageMode}</span>
        <span>SourceLocationGuard · exact / weak reveal</span>
      </div>
    </section>
  );
}
