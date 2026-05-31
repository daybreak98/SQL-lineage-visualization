import type React from 'react';
import { useMemo, useState } from 'react';
import { buildPathContext, currentEntitySet, diagnosticsForEntity, entityName, viewHighlightSets, visibleGraph } from '../data/selectors';
import type { GraphEdge, GraphNode, WorkbenchState } from '../types/lineage';
import { cx } from '../utils/cx';

interface Props {
  state: WorkbenchState;
  setState: React.Dispatch<React.SetStateAction<WorkbenchState>>;
  /** Called when a graph node is double-clicked → navigate to SQL */
  onNodeDoubleClick?: (entityId: string) => void;
}

function edgeLabel(type: string) {
  return type === 'subq' ? 'subq' : type === 'expr' ? 'expr' : type === 'join' ? 'join' : type;
}

export function LineageCanvas({ state, setState, onNodeDoubleClick }: Props) {
  const graph = useMemo(() => visibleGraph(state), [state]);
  const current = useMemo(() => currentEntitySet(state), [state]);
  const highlights = useMemo(() => viewHighlightSets(state), [state]);
  const selectedEdges = useMemo(() => {
    const eid = state.selectedEntity;
    if (!eid || eid === 'out:group') return new Set<string>();
    const ids = new Set<string>();
    graph.edges.forEach(e => {
      if (e.source === eid || e.target === eid) ids.add(e.id);
    });
    return ids;
  }, [state.selectedEntity, graph.edges]);
  // Nodes connected to selected entity (or selected entity itself)
  const selectedNodeIds = useMemo(() => {
    const eid = state.selectedEntity;
    if (!eid || eid === 'out:group') return new Set<string>();
    const ids = new Set<string>();
    graph.edges.forEach(e => {
      if (e.source === eid || e.target === eid) {
        ids.add(e.source);
        ids.add(e.target);
      }
    });
    return ids;
  }, [state.selectedEntity, graph.edges]);
  const hasActiveSelection = state.selectedEntity && state.selectedEntity !== 'out:group';
  const [drag, setDrag] = useState<{ id: string; ox: number; oy: number } | null>(null);
  const [zoom, setZoom] = useState(1.25);
  const pc = buildPathContext(state);
  const gvm = state.graphViewMode ?? 'table';
  const byEntity = Object.fromEntries(graph.nodes.map((n) => [n.entityId, n]));
  const positions = { ...Object.fromEntries(graph.nodes.map((n) => [n.id, { x: n.x, y: n.y }])), ...state.positions };

  const startDrag = (event: React.MouseEvent, node: GraphNode) => {
    event.stopPropagation();
    const rect = (event.currentTarget.parentElement?.parentElement as HTMLElement)?.getBoundingClientRect();
    const p = positions[node.id] ?? { x: node.x, y: node.y };
    setDrag({ id: node.id, ox: (event.clientX - rect.left) / zoom - p.x, oy: (event.clientY - rect.top) / zoom - p.y });
  };

  const move = (event: React.MouseEvent) => {
    if (!drag) return;
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    setState((s) => ({
      ...s,
      positions: { ...s.positions, [drag.id]: { x: Math.max(0, (event.clientX - rect.left) / zoom - drag.ox), y: Math.max(0, (event.clientY - rect.top) / zoom - drag.oy) } },
    }));
  };

  return (
    <div className="viewport" onMouseMove={move} onMouseUp={() => setDrag(null)} style={{ position: 'relative' }}>
      <div style={{ position: 'absolute', top: 4, right: 4, zIndex: 50, display: 'flex', gap: 4 }}>
        <button className="btn h-[24px] px-2 text-[11px]" onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}>−</button>
        <span className="pill" style={{ minWidth: 48, textAlign: 'center' }}>{Math.round(zoom * 100)}%</span>
        <button className="btn h-[24px] px-2 text-[11px]" onClick={() => setZoom((z) => Math.min(3, z + 0.25))}>+</button>
        <button className="btn h-[24px] px-2 text-[11px]" onClick={() => setZoom(1.25)}>Reset</button>
      </div>
      {!(state.pageMode === 'analyzed' && state.trustStatus === 'trusted') && <div className="message block">{state.pageMode === 'failed' ? 'Analysis failed · Search disabled · fix SQL and re-analyze.' : state.pageMode === 'empty' ? 'Paste SQL or load example.' : 'Analyze SQL to build subquery dependency view.'}</div>}
      <div className={cx('mode-tip', ['subquery_dependency', 'large_graph', 'full_graph_preview', 'focus_field'].includes(state.renderMode) && 'show')}>
        {state.renderMode === 'subquery_dependency' ? 'Default Subquery Dependency View · field entities preserved, hidden by default' : state.renderMode === 'full_graph_preview' ? 'Full Graph Preview · user-triggered only' : state.renderMode === 'focus_field' ? 'Focus Field Mode · local field expansion' : 'Large Graph Mode · render degradation, not failed'}
      </div>
      <div className={cx('path-anchor', state.renderMode !== 'subquery_dependency' && state.detailMode !== 'expanded' && 'show')}>
        <div className="path-anchor-title"><span className={cx('dot', pc.status === 'stale' && 'stale', ['partial', 'low_confidence'].includes(pc.status) && 'warn')} /><span>{state.selectedOutput ? `${pc.display} · ${pc.status}` : 'Choose output'}</span></div>
        <div className="path-anchor-body">{state.selectedOutput ? `PathContextStore · ${pc.nodes} nodes · ${pc.mappings} mappings · ${pc.warnings} warnings` : 'Default view shows subquery / CTE dependency.'}</div>
      </div>
      <div className="stage" style={{ transform: `scale(${zoom})`, transformOrigin: 'top left' }} onClick={() => setState((s) => ({ ...s, selectedMapping: null }))}>
        <svg className="edge-layer">
          <defs>
            <marker id="arrowDefault" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L8,3 z" fill="#94A3B8" /></marker>
            <marker id="arrowPrimary" markerWidth="9" markerHeight="9" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L8,3 z" fill="#2563EB" /></marker>
          </defs>
          {graph.edges.map((edge: GraphEdge) => {
            const s = byEntity[edge.source];
            const t = byEntity[edge.target];
            if (!s || !t) return null;
            const sp = positions[s.id] ?? { x: s.x, y: s.y };
            const tp = positions[t.id] ?? { x: t.x, y: t.y };
            const sx = sp.x + 138;
            const sy = sp.y + 18;
            const tx = tp.x;
            const ty = tp.y + 18;
            const isCurrent = (current.has(edge.source) && current.has(edge.target)) || state.selectedMapping === edge.mapping;
            const isSelectedEdge = selectedEdges.has(edge.id);
            const isRelated = isSelectedEdge || (selectedNodeIds.has(edge.source) && selectedNodeIds.has(edge.target));
            const dimmed = hasActiveSelection && !isRelated;
            const isViewHighlighted = highlights.highlightedEdgeIds.has(edge.id);
            const markerEnd = (isCurrent || isSelectedEdge) ? 'url(#arrowPrimary)' : 'url(#arrowDefault)';
            return (
              <g key={edge.id} onClick={(event) => { event.stopPropagation(); if (edge.mapping) setState((st) => ({ ...st, selectedMapping: edge.mapping!, selectedEntity: edge.target, detailMode: 'compact', detailTab: 'mapping' })); }}>
                <path className="edge-hit" d={`M ${sx} ${sy} C ${sx + 82} ${sy}, ${tx - 82} ${ty}, ${tx} ${ty}`} />
                <path className={cx('edge', edge.type, isCurrent && 'current', dimmed && 'dimmed', isViewHighlighted && 'view-highlight', isSelectedEdge && 'edge-selected')} d={`M ${sx} ${sy} C ${sx + 82} ${sy}, ${tx - 82} ${ty}, ${tx} ${ty}`} markerEnd={markerEnd} />
                <text className={cx('edge-label', (isCurrent || isSelectedEdge) && edge.mapping && !drag && 'show')} x={(sx + tx) / 2 - 18} y={(sy + ty) / 2 - 6}>{edgeLabel(edge.type)}</text>
              </g>
            );
          })}
        </svg>
        {graph.nodes.map((node) => {
          const p = positions[node.id] ?? { x: node.x, y: node.y };
          const selected = state.selectedEntity === node.entityId;
          const isCurrent = current.has(node.entityId);
          const inSelection = hasActiveSelection && selectedNodeIds.has(node.entityId);
          const dimmed = hasActiveSelection && !selected && !inSelection;
          const warning = diagnosticsForEntity(state, node.entityId).length > 0 || node.type === 'unknown';
          const isViewHighlighted = highlights.highlightedEntityIds.has(node.entityId);
          return (
            <div key={node.id} className="node" style={{ left: p.x, top: p.y }} data-type={node.type} data-selected={selected || undefined} data-current={isCurrent || undefined} data-warning={warning || undefined} data-stale={state.trustStatus === 'stale' || undefined} data-dimmed={dimmed || undefined} data-dragging={drag?.id === node.id || undefined} data-view-highlight={isViewHighlighted || undefined} onMouseDown={(e) => startDrag(e, node)} onClick={(e) => { e.stopPropagation(); setState((s) => ({ ...s, selectedEntity: node.entityId, selectedMapping: null, detailMode: 'compact', detailTab: 'summary' })); }} onDoubleClick={(e) => { e.stopPropagation(); onNodeDoubleClick?.(node.entityId); }}>
              <span className="strip" /><span className="title" title={node.label}>{node.label}</span>{node.tag && <span className="tag">{node.tag}</span>}<span className="state-dot" />
            </div>
          );
        })}
      </div>
      <div className="stats"><h4>GraphRenderMode</h4><div className="stats-grid"><span>mode</span><b>{state.renderMode.replace('_dependency', '').replace('current_field_', 'field_')}</b><span>view</span><b>{gvm}</b><span>visible</span><b>{graph.nodes.length}/{graph.edges.length}</b><span>layout</span><b>{state.lastTransition?.includes('layout:recompute') ? 'recomputed' : 'stable'}</b><span>labels</span><b>{drag ? 'off' : 'lazy'}</b></div></div>
    </div>
  );
}
