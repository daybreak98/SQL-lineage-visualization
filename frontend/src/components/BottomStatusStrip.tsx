import type { FC } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';

/**
 * BottomStatusStrip — 底部状态条
 *
 * §4.3 硬规则 2: dirty 状态下同步 stale
 * §4.3 硬规则 5: partial 不是 failed
 * §4.3 硬规则 6: failed 状态下显示错误摘要
 *
 * §6.1 单源原则: BottomStatusStrip 消费 PathContextStore，不得自己维护 selected field
 */
const BottomStatusStrip: FC = () => {
  const pageMode = useWorkbenchStore((s) => s.pageMode);
  const analysisStatus = useWorkbenchStore((s) => s.analysisStatus);
  const trustStatus = useWorkbenchStore((s) => s.trustStatus);
  const staleReason = useWorkbenchStore((s) => s.staleReason);
  const pathStatus = useWorkbenchStore((s) => s.pathStatus);
  const unresolvedCount = useWorkbenchStore((s) => s.unresolvedCount);
  const confidenceLevel = useWorkbenchStore((s) => s.confidenceLevel);

  const statusItems: string[] = [];

  // §4.2 状态映射
  if (pageMode === 'empty') {
    statusItems.push('No SQL');
  } else if (pageMode === 'ready') {
    statusItems.push('Ready to analyze');
  } else if (pageMode === 'analyzing') {
    statusItems.push('Analyzing...');
  } else if (pageMode === 'analyzed') {
    if (analysisStatus === 'partial') {
      statusItems.push('Analysis partial');
      if (unresolvedCount) {
        statusItems.push(`${unresolvedCount} unresolved`);
      }
    } else {
      statusItems.push('Analysis complete');
    }
    if (trustStatus === 'stale') {
      statusItems.push(staleReason === 'sql_changed' ? 'SQL changed' : 'Stale');
    }
  } else if (pageMode === 'dirty') {
    statusItems.push('SQL changed');
    statusItems.push('Re-analyze required');
  } else if (pageMode === 'failed') {
    statusItems.push('Analysis failed');
  }

  if (pathStatus === 'stale') {
    statusItems.push('Path stale');
  }
  if (confidenceLevel === 'low' || confidenceLevel === 'unknown') {
    statusItems.push('Low confidence');
  }

  return (
    <div className="bottom-status-strip" data-page-mode={pageMode} data-trust={trustStatus}>
      <div className="status-strip-left">
        {statusItems.map((item, i) => (
          <span key={i} className="status-strip-item">
            {item}
          </span>
        ))}
      </div>
      <div className="status-strip-right">
        {trustStatus === 'stale' && <span className="status-strip-stale">⚠ Stale</span>}
        {pageMode === 'dirty' && <span className="status-strip-dirty">● Dirty</span>}
        {analysisStatus === 'partial' && <span className="status-strip-partial">◐ Partial</span>}
      </div>
    </div>
  );
};

export default BottomStatusStrip;
