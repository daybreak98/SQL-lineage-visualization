import type { FC } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';

/**
 * CanvasToolbar — §15.2 允许项:
 * Fit Path / Center Selected / Reset Viewport / Path Direction / Legend(icon only)
 *
 * §15.3 禁止常驻: SQL Focus / Graph Focus / Max Canvas
 */
const CanvasToolbar: FC = () => {
  const pageMode = useWorkbenchStore((s) => s.pageMode);
  const selectedEntityId = useWorkbenchStore((s) => s.selectedEntityId);
  const selectedOutputEntityId = useWorkbenchStore((s) => s.selectedOutputEntityId);
  const clearSelection = useWorkbenchStore((s) => s.clearSelection);

  const isAnalyzed = pageMode === 'analyzed' || pageMode === 'dirty';
  const hasSelection = !!(selectedEntityId || selectedOutputEntityId);

  const handleFitPath = () => {
    // TODO: 实现 fitPath（React Flow fitView 到当前路径）
  };

  const handleCenterSelected = () => {
    // TODO: 居中选中的节点/边
  };

  const handleResetViewport = () => {
    // TODO: 重置视口 (React Flow fitView)
    clearSelection();
  };

  if (!isAnalyzed) return null;

  return (
    <div className="canvas-toolbar" data-page-mode={pageMode}>
      {/* §15.2 Fit Path */}
      <button
        className="canvas-toolbar-btn"
        onClick={handleFitPath}
        disabled={!hasSelection}
        title="Fit Path (Ctrl+Shift+F)"
      >
        ⊞
      </button>
      {/* §15.2 Center Selected */}
      <button
        className="canvas-toolbar-btn"
        onClick={handleCenterSelected}
        disabled={!hasSelection}
        title="Center Selected"
      >
        ⊙
      </button>
      {/* §15.2 Reset Viewport */}
      <button
        className="canvas-toolbar-btn"
        onClick={handleResetViewport}
        title="Reset Viewport"
      >
        ↺
      </button>
      {/* §15.2 Legend (icon only) */}
      <button className="canvas-toolbar-btn" title="Legend">
        ?
      </button>
    </div>
  );
};

export default CanvasToolbar;
