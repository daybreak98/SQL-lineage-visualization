import { type FC, useState, useCallback } from 'react';
import TopBar from '../components/TopBar';
import SqlEditor from '../components/SqlEditor';
import LineageCanvas from '../components/LineageCanvas';
import CanvasTopSearchBar from '../components/CanvasTopSearchBar';
import CanvasToolbar from '../components/CanvasToolbar';
import CanvasBottomDetailPanel from '../components/CanvasBottomDetailPanel';
import Splitter from '../components/Splitter';
import BottomStatusStrip from '../components/BottomStatusStrip';
import { useWorkbenchStore } from '../stores/workbenchStore';

/**
 * WorkbenchPage — 主工作台页面
 *
 * 布局：
 * ┌──────────────────────────────────────┐
 * │ TopBar                               │
 * ├───────────────┬──────────────────────┤
 * │ SqlEditor     │ LineageCanvas        │
 * │               │ CanvasTopSearchBar   │
 * │               │ CanvasToolbar        │
 * │               │                      │
 * │               │ BottomDetailPanel    │
 * ├───────────────┴──────────────────────┤
 * │ BottomStatusStrip                    │
 * └──────────────────────────────────────┘
 */

const WorkbenchPage: FC = () => {
  const pageMode = useWorkbenchStore((s) => s.pageMode);
  const [splitRatio, setSplitRatio] = useState(0.4);

  const handleSplitRatioChange = useCallback((ratio: number) => {
    setSplitRatio(ratio);
  }, []);

  return (
    <div className="workbench-page" data-page-mode={pageMode}>
      <TopBar />
      <div className="workbench-body">
        <div
          className="workbench-editor-pane"
          style={{ width: `${splitRatio * 100}%` }}
        >
          <SqlEditor />
        </div>
        <Splitter direction="horizontal" initialRatio={splitRatio} onRatioChange={handleSplitRatioChange} />
        <div
          className="workbench-canvas-pane"
          style={{ width: `${(1 - splitRatio) * 100}%` }}
        >
          <CanvasTopSearchBar />
          <CanvasToolbar />
          <div className="workbench-canvas-area">
            <LineageCanvas />
          </div>
          <CanvasBottomDetailPanel />
        </div>
      </div>
      <BottomStatusStrip />
    </div>
  );
};

export default WorkbenchPage;
