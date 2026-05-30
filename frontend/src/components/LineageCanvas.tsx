import { useCallback, useMemo, useEffect, type FC } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import LineageNode from './nodes/LineageNode';
import { useWorkbenchStore } from '../stores/workbenchStore';
import type { LineageNodeData } from './nodes/LineageNode';
import type {
  SubqueryDependencyViewModel,
  TableSummaryNode,
  CteSummaryNode,
  SubquerySummaryNode,
  OutputGroupNode,
  OutputFieldNode,
  ExpressionGroupNode,
  DependencySummaryEdge,
} from '../types/graph';

/**
 * LineageCanvas — React Flow 画布
 *
 * §7 GraphRenderMode State Machine:
 * - ANALYZE_SUCCESS → subquery_dependency (fitView but no field nodes)
 * - SELECT_OUTPUT_FIELD → current_field_path
 *
 * §7.4 硬规则:
 * - ANALYZE_SUCCESS 可 fitView 但不展开字段节点
 * - SELECT_OUTPUT_FIELD 只请求 path patch，不重算全图布局
 *
 * §12 CSS/data-state: 节点视觉通过 data-node-type 等属性实现
 */

const nodeTypes = {
  lineageNode: LineageNode,
};

/** 将 SubqueryDependencyViewModel 转为 React Flow nodes */
function buildNodes(
  viewModel: SubqueryDependencyViewModel | undefined,
  currentPathEntityIds: Set<string>,
  selectedEntityId: string | undefined,
  trustStatus: string,
): Node[] {
  if (!viewModel) return [];

  return viewModel.nodes.map((n, index) => {
    const baseX = (index % 5) * 220 + 50;
    const baseY = Math.floor(index / 5) * 100 + 50;

    const entityId = 'entity_id' in n ? n.entity_id : '';
    const isSelected = entityId === selectedEntityId;
    const isCurrentPath = currentPathEntityIds.has(entityId);
    const isStale = trustStatus === 'stale';

    const nodeData: LineageNodeData = {
      entity_id: entityId,
      node_type: n.node_type,
      label: n.label,
      selected: isSelected,
      currentPath: isCurrentPath,
      stale: isStale,
      dimmed: false,
    };

    // 按类型填充额外字段
    if (n.node_type === 'table') {
      const t = n as TableSummaryNode;
      nodeData.catalog = t.catalog;
      nodeData.schema = t.schema;
      nodeData.table = t.table;
      nodeData.alias = t.alias;
    } else if (n.node_type === 'cte') {
      const c = n as CteSummaryNode;
      nodeData.cte_name = c.cte_name;
    } else if (n.node_type === 'subquery') {
      const s = n as SubquerySummaryNode;
      nodeData.alias = s.alias;
      nodeData.subquery_n = s.subquery_n;
      nodeData.tags = s.tags;
    } else if (n.node_type === 'output_group') {
      const o = n as OutputGroupNode;
      nodeData.field_count = o.field_count;
      nodeData.default_outputs = o.default_outputs;
    } else if (n.node_type === 'output_field') {
      const of = n as OutputFieldNode;
      nodeData.data_type = of.data_type;
    } else if (n.node_type === 'expression_group') {
      const eg = n as ExpressionGroupNode;
      nodeData.expression_type = eg.expression_type;
    }

    return {
      id: n.id,
      type: 'lineageNode',
      position: { x: baseX, y: baseY },
      data: nodeData,
    };
  });
}

/** 将 DependencySummaryEdge 转为 React Flow edges */
function buildEdges(
  viewModel: SubqueryDependencyViewModel | undefined,
  currentPathEdgeIds: Set<string>,
  selectedEdgeMappingId: string | undefined,
): Edge[] {
  if (!viewModel) return [];

  return viewModel.edges.map((e: DependencySummaryEdge) => {
    const isSelected = e.id === selectedEdgeMappingId;
    const isCurrentPath = currentPathEdgeIds.has(e.id);

    let className = 'lineage-edge';
    if (isSelected || isCurrentPath) className += ' lineage-edge--highlighted';
    if (e.edge_type === 'join_dependency' || e.edge_type === 'filter_dependency') {
      className += ' lineage-edge--semantic';
    }

    return {
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      type: 'smoothstep',
      animated: isCurrentPath,
      className,
      style: isSelected || isCurrentPath ? { strokeWidth: 2.5 } : undefined,
    };
  });
}

const LineageCanvas: FC = () => {
  const viewModel = useWorkbenchStore((s) => s.subqueryDependencyViewModel);
  const renderMode = useWorkbenchStore((s) => s.renderMode);
  const trustStatus = useWorkbenchStore((s) => s.trustStatus);
  const selectedEntityId = useWorkbenchStore((s) => s.selectedEntityId);
  const selectedEdgeMappingId = useWorkbenchStore((s) => s.selectedEdgeMappingId);
  const selectEntity = useWorkbenchStore((s) => s.selectEntity);
  const selectEdgeMapping = useWorkbenchStore((s) => s.selectEdgeMapping);
  const clearSelection = useWorkbenchStore((s) => s.clearSelection);

  // TODO M5: 从 PathContextStore 获取 pathRef 用于高亮
  const currentPathNodeIds = useMemo(() => new Set<string>(), []);
  const currentPathEdgeIds = useMemo(() => new Set<string>(), []);

  const nodes = useMemo(
    () => buildNodes(viewModel, currentPathNodeIds, selectedEntityId, trustStatus),
    [viewModel, currentPathNodeIds, selectedEntityId, trustStatus],
  );

  const edges = useMemo(
    () => buildEdges(viewModel, currentPathEdgeIds, selectedEdgeMappingId),
    [viewModel, currentPathEdgeIds, selectedEdgeMappingId],
  );

  const [nodesState, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edgesState, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // §7.4 硬规则: ANALYZE_SUCCESS 可以 fitView，SELECT_OUTPUT_FIELD 只请求 path patch
  useEffect(() => {
    setNodes(nodes);
    setEdges(edges);
  }, [nodes, edges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      selectEntity(node.id);
    },
    [selectEntity],
  );

  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      selectEdgeMapping(edge.id);
    },
    [selectEdgeMapping],
  );

  const onPaneClick = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  return (
    <div className="lineage-canvas" data-render-mode={renderMode}>
      <ReactFlow
        nodes={nodesState}
        edges={edgesState}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView={renderMode === 'subquery_dependency' && nodesState.length > 0}
        connectionLineType={ConnectionLineType.SmoothStep}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        minZoom={0.1}
        maxZoom={2}
        // §17: 拖拽性能 — 拖拽不触发 layout、不全局 dispatch、不重算 path
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls position="bottom-right" showInteractive={false} />
        <MiniMap
          position="bottom-left"
          nodeStrokeWidth={3}
          pannable
          zoomable
          style={{ width: 120, height: 80 }}
        />
      </ReactFlow>
      {!viewModel && (
        <div className="lineage-canvas-empty">
          {renderMode === 'subquery_dependency'
            ? 'Write SQL and click Analyze to see lineage'
            : 'No lineage data available'}
        </div>
      )}
    </div>
  );
};

export default LineageCanvas;
