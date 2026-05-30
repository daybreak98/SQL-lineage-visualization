import type { FC } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';

/**
 * CanvasBottomDetailPanel — §18 compact 固定三行结构
 *
 * §18.1 固定三行模板
 * §18.2 禁止：compact 默认出现 4 个以上 Tab、完整 SQL、完整字段注释
 *
 * §17.1 高度预算: compact 84-96px
 */
const CanvasBottomDetailPanel: FC = () => {
  const detailPanelOpen = useWorkbenchStore((s) => s.detailPanelOpen);
  const selectedEntityId = useWorkbenchStore((s) => s.selectedEntityId);
  const selectedEdgeMappingId = useWorkbenchStore((s) => s.selectedEdgeMappingId);
  const selectedOutputEntityId = useWorkbenchStore((s) => s.selectedOutputEntityId);
  const selectedOutputDisplayName = useWorkbenchStore((s) => s.selectedOutputDisplayName);
  const trustStatus = useWorkbenchStore((s) => s.trustStatus);
  const closeDetailPanel = useWorkbenchStore((s) => s.closeDetailPanel);

  if (!detailPanelOpen) {
    return (
      <div className="canvas-detail-panel canvas-detail-panel--collapsed">
        <span className="canvas-detail-collapsed-text">Select a node or edge to see details</span>
      </div>
    );
  }

  // §18.1 选中输出字段时的三行结构
  if (selectedOutputEntityId) {
    return (
      <div className="canvas-detail-panel canvas-detail-panel--compact">
        <div className="canvas-detail-row canvas-detail-row--header">
          <span className="canvas-detail-entity">{selectedOutputDisplayName ?? selectedOutputEntityId}</span>
          <span className="canvas-detail-type">Output Field</span>
          <span className={`canvas-detail-confidence ${trustStatus}`}>
            {trustStatus === 'trusted' ? 'high confidence' : 'stale'}
          </span>
        </div>
        <div className="canvas-detail-row canvas-detail-row--mapping">
          <span className="canvas-detail-mapping-text">
            Select a source-to-target mapping for details
          </span>
        </div>
        <div className="canvas-detail-row canvas-detail-row--actions">
          <button className="canvas-detail-action">Locate SQL</button>
          <button className="canvas-detail-action">Focus Path</button>
          <button className="canvas-detail-action">View Mapping</button>
        </div>
      </div>
    );
  }

  // §18.1 选中节点
  if (selectedEntityId) {
    return (
      <div className="canvas-detail-panel canvas-detail-panel--compact">
        <div className="canvas-detail-row canvas-detail-row--header">
          <span className="canvas-detail-entity">{selectedEntityId}</span>
          <span className="canvas-detail-type">Node</span>
          <span className={`canvas-detail-confidence ${trustStatus}`}>
            {trustStatus === 'trusted' ? 'trusted' : 'stale'}
          </span>
        </div>
        <div className="canvas-detail-row canvas-detail-row--summary">
          <span className="canvas-detail-summary-text">
            Select a node to view upstream and downstream details
          </span>
        </div>
        <div className="canvas-detail-row canvas-detail-row--actions">
          <button className="canvas-detail-action">Locate SQL</button>
          <button className="canvas-detail-action">Focus Path</button>
          <button className="canvas-detail-action">Expand</button>
        </div>
      </div>
    );
  }

  // §18.1 选中边
  if (selectedEdgeMappingId) {
    return (
      <div className="canvas-detail-panel canvas-detail-panel--compact">
        <div className="canvas-detail-row canvas-detail-row--header">
          <span className="canvas-detail-entity">{selectedEdgeMappingId}</span>
          <span className="canvas-detail-type">Edge Mapping</span>
          <span className={`canvas-detail-confidence ${trustStatus}`}>
            {trustStatus === 'trusted' ? 'trusted' : 'stale'}
          </span>
        </div>
        <div className="canvas-detail-row canvas-detail-row--mapping">
          <span className="canvas-detail-mapping-text">
            Edge mapping details will appear here
          </span>
        </div>
        <div className="canvas-detail-row canvas-detail-row--actions">
          <button className="canvas-detail-action">Locate SQL</button>
          <button className="canvas-detail-action">View Mapping</button>
          <button className="canvas-detail-action">Expand</button>
        </div>
      </div>
    );
  }

  return (
    <div className="canvas-detail-panel canvas-detail-panel--collapsed">
      <button className="canvas-detail-close" onClick={closeDetailPanel}>
        Close
      </button>
    </div>
  );
};

export default CanvasBottomDetailPanel;
