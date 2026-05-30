import type { FC } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

/**
 * LineageNode — §10 Node Visual Taxonomy 统一节点组件
 *
 * §12 CSS/data-state 约束：
 * - className="lineage-node"
 * - data-node-type={nodeType}
 * - data-selected / data-current-path / data-warning / data-error / data-stale / data-dimmed
 *
 * §11.1 状态优先级：selected > error > current_path > search_hit > warning > stale > hover > dimmed > normal
 */

export interface LineageNodeData {
  [key: string]: unknown;
  entity_id: string;
  node_type: 'table' | 'cte' | 'subquery' | 'output_group' | 'output_field' | 'expression_group' | 'unknown';
  label: string;
  // table
  catalog?: string;
  schema?: string;
  table?: string;
  alias?: string;
  // cte
  cte_name?: string;
  // subquery
  subquery_n?: string;
  tags?: string[];
  // output
  field_count?: number;
  default_outputs?: string[];
  data_type?: string;
  // expression
  expression_type?: string;
  // states
  selected?: boolean;
  currentPath?: boolean;
  warning?: boolean;
  error?: boolean;
  stale?: boolean;
  dimmed?: boolean;
}

const LineageNode: FC<NodeProps> = ({ data }) => {
  const nodeData = data as unknown as LineageNodeData;
  const {
    node_type,
    label,
    alias,
    cte_name,
    subquery_n,
    tags,
    field_count,
    expression_type,
    selected,
    currentPath,
    warning,
    error,
    stale,
    dimmed,
  } = nodeData;

  // §11.1 状态优先级确定主状态
  const primaryState = selected
    ? 'selected'
    : error
    ? 'error'
    : currentPath
    ? 'current_path'
    : warning
    ? 'warning'
    : stale
    ? 'stale'
    : dimmed
    ? 'dimmed'
    : 'normal';

  // §10.4 节点正文：允许展示的内容
  const displayLabel = label || cte_name || subquery_n || '?';
  const subtitle = (() => {
    const parts: string[] = [];
    if (alias && node_type === 'table') parts.push(alias);
    if (tags && tags.length > 0) parts.push(tags.slice(0, 2).join(' · '));
    if (expression_type) parts.push(expression_type);
    return parts.join(' · ');
  })();

  // §10.2 badge
  const badge = (() => {
    switch (node_type) {
      case 'output_group':
      case 'output_field':
        return 'OUT';
      case 'subquery':
        return 'SUBQ';
      case 'cte':
        return 'CTE';
      case 'expression_group':
        return 'EXPR';
      case 'unknown':
        return '?';
      default:
        return undefined;
    }
  })();

  const hasHandles = node_type !== 'unknown';

  return (
    <div
      className="lineage-node"
      data-node-type={node_type}
      data-selected={selected || undefined}
      data-current-path={currentPath || undefined}
      data-warning={warning || undefined}
      data-error={error || undefined}
      data-stale={stale || undefined}
      data-dimmed={dimmed || undefined}
      data-primary-state={primaryState}
    >
      {hasHandles && <Handle type="target" position={Position.Top} className="lineage-handle" />}
      <div className="lineage-node-body">
        {badge && <span className="lineage-node-badge">{badge}</span>}
        <span className="lineage-node-label">{displayLabel}</span>
        {subtitle && <span className="lineage-node-subtitle">{subtitle}</span>}
        {node_type === 'output_group' && field_count !== undefined && (
          <span className="lineage-node-count">{field_count} fields</span>
        )}
      </div>
      {hasHandles && <Handle type="source" position={Position.Bottom} className="lineage-handle" />}
    </div>
  );
};

export default LineageNode;
