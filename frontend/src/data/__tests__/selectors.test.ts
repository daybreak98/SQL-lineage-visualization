import { describe, it, expect } from 'vitest';
import { subqueryNodes, subqueryEdges, paths, diagnostics } from '../mockLineage';
import {
  visibleGraph,
  buildPathContext,
  currentEntitySet,
  diagnosticsOf,
  entityName,
  entityOf,
  deriveAttention,
  fieldNodes,
  fieldEdges,
  transitionRenderMode,
} from '../selectors';
import type { WorkbenchState } from '../../types/lineage';

function baseState(overrides: Partial<WorkbenchState> = {}): WorkbenchState {
  return {
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
    positions: {},
    ...overrides,
  };
}

describe('selectors', () => {
  describe('visibleGraph', () => {
    it('returns subquery nodes/edges for semantics view mode without backendGraph', () => {
      const state = baseState({ graphViewMode: 'semantics' });
      const graph = visibleGraph(state);
      expect(graph.nodes).toEqual(subqueryNodes);
      expect(graph.edges).toEqual(subqueryEdges);
    });

    it('returns backendGraph when present for semantics view mode', () => {
      const backendGraph = { nodes: [subqueryNodes[0]], edges: [subqueryEdges[0]] };
      const state = baseState({ graphViewMode: 'semantics', backendGraph });
      const graph = visibleGraph(state);
      expect(graph.nodes).toEqual(backendGraph.nodes);
      expect(graph.edges).toEqual(backendGraph.edges);
    });

    it('returns field-level nodes/edges for column view mode', () => {
      const state = baseState({ graphViewMode: 'column', selectedOutput: 'out:order_cnt' });
      const graph = visibleGraph(state);
      expect(graph.nodes.length).toBeGreaterThan(0);
      expect(graph.edges.length).toBeGreaterThan(0);
    });

    it('returns only table and output nodes in table view mode', () => {
      const state = baseState({ graphViewMode: 'table' });
      const graph = visibleGraph(state);
      for (const node of graph.nodes) {
        expect(['table', 'output']).toContain(node.type);
      }
      // Should have fewer nodes than full subquery graph (filters out CTE/subquery)
      expect(graph.nodes.length).toBeLessThan(subqueryNodes.length);
    });
  });

  describe('buildPathContext', () => {
    it('returns idle when no output selected', () => {
      const state = baseState({ selectedOutput: null });
      const pc = buildPathContext(state);
      expect(pc.status).toBe('idle');
      expect(pc.display).toBe('Choose output');
    });

    it('returns ready with correct display for selected output', () => {
      const state = baseState({ selectedOutput: 'out:order_cnt' });
      const pc = buildPathContext(state);
      expect(pc.status).toBe('ready');
      expect(pc.display).toBe('order_cnt');
      expect(pc.nodes).toBe(paths['out:order_cnt']?.length ?? 0);
    });

    it('returns stale when trustStatus is stale', () => {
      const state = baseState({ selectedOutput: 'out:order_cnt', trustStatus: 'stale' });
      const pc = buildPathContext(state);
      expect(pc.status).toBe('stale');
    });

    it('returns partial when analysisStatus is partial', () => {
      const state = baseState({ selectedOutput: 'out:order_cnt', analysisStatus: 'partial' });
      const pc = buildPathContext(state);
      expect(pc.status).toBe('partial');
    });

    it('returns low_confidence for avg_order_amount output', () => {
      const state = baseState({ selectedOutput: 'out:avg_order_amount' });
      const pc = buildPathContext(state);
      expect(pc.status).toBe('low_confidence');
      expect(pc.confidence).toBe('medium');
    });
  });

  describe('currentEntitySet', () => {
    it('returns entity IDs for semantics view mode', () => {
      const state = baseState({ graphViewMode: 'semantics' });
      const set = currentEntitySet(state);
      for (const node of subqueryNodes) {
        expect(set.has(node.entityId)).toBe(true);
      }
      expect(set.size).toBe(subqueryNodes.length);
    });

    it('returns entity IDs from current path when in column view mode', () => {
      const state = baseState({ graphViewMode: 'column', selectedOutput: 'out:order_cnt' });
      const set = currentEntitySet(state);
      const pathIds = paths['out:order_cnt'] ?? [];
      for (const id of pathIds) {
        expect(set.has(id)).toBe(true);
      }
    });

    it('falls back to out:order_cnt path when no output selected in column view', () => {
      const state = baseState({ graphViewMode: 'column', selectedOutput: null });
      const set = currentEntitySet(state);
      const pathIds = paths['out:order_cnt'] ?? [];
      for (const id of pathIds) {
        expect(set.has(id)).toBe(true);
      }
    });
  });

  describe('diagnosticsOf', () => {
    it('returns diagnostics for a matching entity', () => {
      const result = diagnosticsOf('out:avg_order_amount');
      expect(result.length).toBeGreaterThan(0);
      expect(result.every((d) => d.entityId === 'out:avg_order_amount')).toBe(true);
    });

    it('returns empty array for entity with no diagnostics', () => {
      const result = diagnosticsOf('table:dwd_order_di');
      expect(result).toEqual([]);
    });

    it('returns empty array for null entityId', () => {
      expect(diagnosticsOf(null)).toEqual([]);
      expect(diagnosticsOf(undefined)).toEqual([]);
    });
  });

  describe('entityName', () => {
    it('returns entity name for valid id', () => {
      expect(entityName('table:dwd_order_di')).toBe('dwd_order_di');
      expect(entityName('out:order_cnt')).toBe('order_cnt');
    });

    it('returns dash for null/empty id', () => {
      expect(entityName(null)).toBe('-');
      expect(entityName(undefined)).toBe('-');
    });
  });

  describe('entityOf', () => {
    it('returns entity for valid id', () => {
      const entity = entityOf('table:dwd_order_di');
      expect(entity).toBeDefined();
      expect(entity!.name).toBe('dwd_order_di');
    });

    it('returns undefined for unknown id', () => {
      expect(entityOf('nonexistent')).toBeUndefined();
    });

    it('returns undefined for null/empty id', () => {
      expect(entityOf(null)).toBeUndefined();
      expect(entityOf(undefined)).toBeUndefined();
    });
  });

  describe('deriveAttention', () => {
    it('returns empty_guide for empty pageMode', () => {
      const [slot, _, category] = deriveAttention(baseState({ pageMode: 'empty' }));
      expect(slot).toBe('empty_guide');
      expect(category).toBe('page_mode');
    });

    it('returns analyze for ready pageMode', () => {
      const [slot] = deriveAttention(baseState({ pageMode: 'ready' }));
      expect(slot).toBe('analyze');
    });

    it('returns error_summary for failed pageMode', () => {
      const [slot, _, category] = deriveAttention(baseState({ pageMode: 'failed' }));
      expect(slot).toBe('error_summary');
      expect(category).toBe('diagnostic');
    });

    it('returns current_path when output is selected', () => {
      const [slot, _, category] = deriveAttention(baseState({ selectedOutput: 'out:order_cnt' }));
      expect(slot).toBe('current_path');
      expect(category).toBe('path_context');
    });
  });

  describe('transitionRenderMode', () => {
    it('transitions to subquery_dependency on ANALYZE_SUCCESS', () => {
      const result = transitionRenderMode('subquery_dependency', 'ANALYZE_SUCCESS');
      expect(result.mode).toBe('subquery_dependency');
    });

    it('transitions to current_field_path on SELECT_OUTPUT_FIELD', () => {
      const result = transitionRenderMode('subquery_dependency', 'SELECT_OUTPUT_FIELD');
      expect(result.mode).toBe('current_field_path');
    });

    it('returns unchanged for unknown event', () => {
      const result = transitionRenderMode('subquery_dependency', 'UNKNOWN_EVENT');
      expect(result.mode).toBe('subquery_dependency');
      expect(result.description).toContain('unchanged');
    });
  });
});
