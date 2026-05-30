import type { FC } from 'react';
import { useWorkbenchStore, selectAttention } from '../stores/workbenchStore';

const getStoreState = () => useWorkbenchStore.getState();

/**
 * TopBar — §15.1 允许项：
 * Analyze / Re-analyze / Cancel / Format / Dialect / Metadata / More
 *
 * §15.3 禁止常驻：SQL Focus / Graph Focus / Max Canvas / Reset Split Ratio
 *
 * §16 Primary CTA Emphasis
 */
const TopBar: FC = () => {
  const pageMode = useWorkbenchStore((s) => s.pageMode);
  const analysisStatus = useWorkbenchStore((s) => s.analysisStatus);
  const trustStatus = useWorkbenchStore((s) => s.trustStatus);
  const sql = useWorkbenchStore((s) => s.sql);
  const dialect = useWorkbenchStore((s) => s.dialect);
  const setSql = useWorkbenchStore((s) => s.setSql);
  const setDialect = useWorkbenchStore((s) => s.setDialect);
  const requestAnalyze = useWorkbenchStore((s) => s.requestAnalyze);
  const attention = useWorkbenchStore(selectAttention);

  const isAnalyzing = analysisStatus === 'running';
  const isDirty = pageMode === 'dirty';
  const isFailed = pageMode === 'failed';
  const isEmpty = pageMode === 'empty';
  const isReady = pageMode === 'ready';
  const isAnalyzed = pageMode === 'analyzed';

  // §16.1 主 CTA 判定
  const handlePrimaryAction = () => {
    if (isEmpty || isReady) {
      requestAnalyze();
    } else if (isAnalyzing) {
      // Cancel — currently no-op for P0
    } else if (isDirty || isFailed) {
      requestAnalyze();
    }
  };

  const getPrimaryButtonLabel = (): string => {
    if (isEmpty) return 'Analyze';
    if (isReady) return 'Analyze';
    if (isAnalyzing) return 'Cancel';
    if (isDirty) return 'Re-analyze';
    if (isFailed) return 'Re-analyze';
    // §16.1 analyzed 后 Analyze 降权
    return 'Analyze';
  };

  const isPrimaryBlue = (): boolean => {
    // §16.2: 任意时刻最多一个主蓝实心按钮
    if (isAnalyzed && attention.primaryFocus !== 'analyze') return false;
    return isEmpty || isReady || isDirty || isFailed;
  };

  const handleLoadExample = () => {
    setSql(
      'SELECT o.order_id, o.amount, c.name\n' +
      'FROM orders o\n' +
      'JOIN customers c ON o.customer_id = c.id\n' +
      'WHERE o.status = \'completed\'',
    );
  };

  const handleFormat = () => {
    // P0: 简单的 SQL 格式化（后续可替换为 formatter 库）
    const formatted = getStoreState().sql
      .replace(/\s+/g, ' ')
      .replace(/\s*,\s*/g, ',\n  ')
      .replace(/ FROM /gi, '\nFROM ')
      .replace(/ WHERE /gi, '\nWHERE ')
      .replace(/ JOIN /gi, '\nJOIN ')
      .replace(/ ON /gi, '\n  ON ')
      .trim();
    setSql(formatted);
  };

  return (
    <div className="topbar" data-page-mode={pageMode}>
      <div className="topbar-left">
        <span className="topbar-brand">SQL Lineage</span>
      </div>
      <div className="topbar-center">
        {/* §15.1 Dialect selector */}
        <select
          className="topbar-dialect"
          value={dialect}
          onChange={(e) => setDialect(e.target.value)}
          aria-label="SQL Dialect"
        >
          <option value="mysql">MySQL</option>
          <option value="postgresql">PostgreSQL</option>
          <option value="hive">Hive</option>
          <option value="spark">Spark SQL</option>
        </select>

        {/* §15.1 Format */}
        <button
          className="topbar-btn topbar-btn--secondary"
          onClick={handleFormat}
          disabled={isAnalyzing || !sql.trim()}
        >
          Format
        </button>

        {/* §15.1 Metadata */}
        <button className="topbar-btn topbar-btn--secondary" disabled>
          Metadata
        </button>

        {/* §15.1 More — §15.4 布局恢复入口 */}
        <div className="topbar-more">
          <button className="topbar-btn topbar-btn--secondary">More</button>
        </div>
      </div>
      <div className="topbar-right">
        {/* §16.1 主 CTA */}
        {isEmpty && (
          <button
            className="topbar-btn topbar-btn--secondary"
            onClick={handleLoadExample}
          >
            Load Example
          </button>
        )}
        <button
          className={
            'topbar-btn' +
            (isPrimaryBlue() ? ' topbar-btn--primary' : ' topbar-btn--secondary') +
            (isAnalyzing ? ' topbar-btn--loading' : '') +
            (isDirty ? ' topbar-btn--stale' : '')
          }
          onClick={handlePrimaryAction}
          disabled={isAnalyzing ? false : (isEmpty ? false : !sql.trim() && isEmpty)}
        >
          {isAnalyzing && <span className="topbar-spinner" />}
          {getPrimaryButtonLabel()}
          {isDirty && <span className="topbar-stale-dot" title="SQL changed — re-analyze required" />}
        </button>
      </div>
    </div>
  );
};

export default TopBar;
