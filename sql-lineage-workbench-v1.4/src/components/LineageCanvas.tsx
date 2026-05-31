import type React from 'react';
import { useMemo, useState } from 'react';
import { buildPathContext, currentEntitySet, diagnosticsOf, entityName, visibleGraph } from '../data/selectors';
import type { GraphEdge, GraphNode, WorkbenchState } from '../types/lineage';
import { cx } from '../utils/cx';

interface Props {
  state: WorkbenchState;
  setState: React.Dispatch<React.SetStateAction<WorkbenchState>>;
}

function edgeLabel(type: string) {
  return type === 'subq' ? 'subq' : type === 'expr' ? 'expr' : type === 'join' ? 'join' : type;
}

export function LineageCanvas({ state, setState }: Props) {
  const graph = useMemo(() => visibleGraph(state), [state]);
  const current = useMemo(() => currentEntitySet(state), [state]);
  const [drag, setDrag] = useState<{ id: string; ox: number; oy: number } | null>(null);
  const pc = buildPathContext(state);
  const byEntity = Object.fromEntries(graph.nodes.map((n) => [n.entityId, n]));
  const positions = { ...Object.fromEntries(graph.nodes.map((n) => [n.id, { x: n.x, y: n.y }])), ...state.positions };

  const startDrag = (event: React.MouseEvent, node: GraphNode) => {
    event.stopPropagation();
    const rect = (event.currentTarget.parentElement?.parentElement as HTMLElement)?.getBoundingClientRect();
    const p = positions[node.id];
    setDrag({ id: node.id, ox: (event.clientX - rect.left) / 0.88 - p.x, oy: (event.clientY - rect.top) / 0.88 - p.y });
  };

  const move = (event: React.MouseEvent) => {
    if (!drag) return;
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    setState((s) => ({
      ...s,
      positions: { ...s.positions, [drag.id]: { x: Math.max(0, (event.clientX - rect.left) / 0.88 - drag.ox), y: Math.max(0, (event.clientY - rect.top) / 0.88 - drag.oy) } },
    }));
  };

  return (
    <div className="viewport" onMouseMove={move} onMouseUp={() => setDrag(null)}>
      {!(state.pageMode === 'analyzed' && state.trustStatus === 'trusted') && <div className="message block">{state.pageMode === 'failed' ? 'Analysis failed · Search disabled · fix SQL and re-analyze.' : state.pageMode === 'empty' ? 'Paste SQL or load example.' : 'Analyze SQL to build subquery dependency view.'}</div>}
      <div className={cx('mode-tip', ['subquery_dependency', 'large_graph', 'full_graph_preview', 'focus_field'].includes(state.renderMode) && 'show')}>
        {state.renderMode === 'subquery_dependency' ? 'Default Subquery Dependency View · field entities preserved, hidden by default' : state.renderMode === 'full_graph_preview' ? 'Full Graph Preview · user-triggered only' : state.renderMode === 'focus_field' ? 'Focus Field Mode · local field expansion' : 'Large Graph Mode · render degradation, not failed'}
      </div>
      <div className={cx('path-anchor', state.renderMode !== 'subquery_dependency' && state.detailMode !== 'expanded' && 'show')}>
        <div className="path-anchor-title"><span className={cx('dot', pc.status === 'stale' && 'stale', ['partial', 'low_confidence'].includes(pc.status) && 'warn')} /><span>{state.selectedOutput ? `${pc.display} · ${pc.status}` : 'Choose output'}</span></div>
        <div className="path-anchor-body">{state.selectedOutput ? `PathContextStore · ${pc.nodes} nodes · ${pc.mappings} mappings · ${pc.warnings} warnings` : 'Default view shows subquery / CTE dependency.'}</div>
      </div>
      <div className="stage" onClick={() => setState((s) => ({ ...s, selectedMapping: null }))}>
        <svg className="edge-layer">
          <defs>
            <marker id="arrowDefault" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L8,3 z" fill="#94A3B8" /></marker>
            <marker id="arrowPrimary" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L8,3 z" fill="#2563EB" /></marker>
          </defs>
          {graph.edges.map((edge: GraphEdge) => {
            const s = byEntity[edge.source];
            const t = byEntity[edge.target];
            if (!s || !t) return null;
            const sp = positions[s.id];
            const tp = positions[t.id];
            const sx = sp.x + 138;
            const sy = sp.y + 18;
            const tx = tp.x;
            const ty = tp.y + 18;
            const isCurrent = (current.has(edge.source) && current.has(edge.target)) || state.selectedMapping === edge.mapping;
            const dimmed = state.renderMode !== 'subquery_dependency' && !isCurrent;
            return (
              <g key={edge.id} onClick={(event) => { event.stopPropagation(); if (edge.mapping) setState((st) => ({ ...st, selectedMapping: edge.mapping!, selectedEntity: edge.target, detailMode: 'compact', detailTab: 'mapping' })); }}>
                <path className="edge-hit" d={`M ${sx} ${sy} C ${sx + 82} ${sy}, ${tx - 82} ${ty}, ${tx} ${ty}`} />
                <path className={cx('edge', edge.type, isCurrent && 'current', dimmed && 'dimmed')} d={`M ${sx} ${sy} C ${sx + 82} ${sy}, ${tx - 82} ${ty}, ${tx} ${ty}`} markerEnd={isCurrent ? 'url(#arrowPrimary)' : 'url(#arrowDefault)'} />
                <text className={cx('edge-label', isCurrent && edge.mapping && !drag && 'show')} x={(sx + tx) / 2 - 18} y={(sy + ty) / 2 - 6}>{edgeLabel(edge.type)}</text>
              </g>
            );
          })}
        </svg>
        {graph.nodes.map((node) => {
          const p = positions[node.id];
          const selected = state.selectedEntity === node.entityId;
          const isCurrent = current.has(node.entityId);
          const dimmed = state.renderMode !== 'subquery_dependency' && Boolean(state.selectedOutput) && !isCurrent;
          const warning = diagnosticsOf(node.entityId).length > 0 || node.type === 'unknown';
          return (
            <div key={node.id} className="node" data-type={node.type} data-selected={selected || undefined} data-current={isCurrent || undefined} data-warning={warning || undefined} data-stale={state.trustStatus === 'stale' || undefined} data-dimmed={dimmed || undefined} data-dragging={drag?.id === node.id || undefined} style={{ transform: `translate(${p.x}px,${p.y}px)` }} onMouseDown={(e) => startDrag(e, node)} onClick={(e) => { e.stopPropagation(); setState((s) => ({ ...s, selectedEntity: node.entityId, selectedMapping: null, detailMode: 'compact', detailTab: 'summary' })); }}>
              <span className="strip" /><span className="title" title={node.label}>{node.label}</span>{node.tag && <span className="tag">{node.tag}</span>}<span className="state-dot" />
            </div>
          );
        })}
      </div>
      <div className="stats"><h4>GraphRenderMode</h4><div className="stats-grid"><span>mode</span><b>{state.renderMode.replace('_dependency', '').replace('current_field_', 'field_')}</b><span>visible</span><b>{graph.nodes.length}/{graph.edges.length}</b><span>layout</span><b>{state.lastTransition?.includes('layout:recompute') ? 'recomputed' : 'stable'}</b><span>labels</span><b>{drag ? 'off' : 'lazy'}</b></div></div>
    </div>
  );
}
