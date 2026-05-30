import { type FC, useState, useCallback } from 'react';
import { useWorkbenchStore, selectCanSelectOutput, selectOutputCapsule } from '../stores/workbenchStore';

/**
 * CanvasTopSearchBar — §14 40px 单行规则
 *
 * 左侧：Search Input
 * 右侧：Output / Current Path Capsule
 *
 * §14.2 宽度响应式（P0 简化实现：≥560px 显示 Search Input + Capsule）
 *
 * §14.3 文案收敛
 */
const CanvasTopSearchBar: FC = () => {
  const pageMode = useWorkbenchStore((s) => s.pageMode);
  const trustStatus = useWorkbenchStore((s) => s.trustStatus);
  const subqueryDependencyViewModel = useWorkbenchStore((s) => s.subqueryDependencyViewModel);
  const selectOutputField = useWorkbenchStore((s) => s.selectOutputField);
  const canSelectOutput = useWorkbenchStore(selectCanSelectOutput);
  const outputCapsule = useWorkbenchStore(selectOutputCapsule);

  const [searchText, setSearchText] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const isDisabled = !canSelectOutput || pageMode === 'failed' || pageMode === 'dirty';

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchText(e.target.value);
    setShowSuggestions(e.target.value.length > 0);
  }, []);

  const handleSelectDefaultOutput = useCallback(
    (entityId: string, displayName: string) => {
      selectOutputField(entityId, displayName);
      setShowSuggestions(false);
      setSearchText('');
    },
    [selectOutputField],
  );

  // §14.3 文案
  const getPlaceholder = (): string => {
    if (pageMode === 'dirty' || trustStatus === 'stale') return 'Search disabled until re-analyze';
    if (pageMode === 'failed') return 'Search disabled';
    if (outputCapsule.status === 'chosen') return 'Search another field...';
    return 'Search field, table, alias...';
  };

  const getCapsuleText = (): string => {
    if (outputCapsule.status === 'empty') return 'Choose output field';
    if (outputCapsule.status === 'stale') return `${outputCapsule.display_name} path stale`;
    if (outputCapsule.status === 'partial') return `${outputCapsule.display_name} · partial`;
    if (outputCapsule.status === 'low_confidence') return `${outputCapsule.display_name} · low`;
    return `Current: ${outputCapsule.display_name}`;
  };

  const defaultOutputs = subqueryDependencyViewModel?.defaultOutputEntityIds ?? [];
  // Map entity IDs to display names from nodes
  const defaultOutputNodes = (subqueryDependencyViewModel?.nodes ?? [])
    .filter((n) => defaultOutputs.includes((n as { entity_id: string }).entity_id))
    .map((n) => ({
      entity_id: (n as { entity_id: string }).entity_id,
      label: n.label,
    }));

  return (
    <div className="canvas-top-search-bar" data-page-mode={pageMode}>
      <div className="canvas-search-input-wrapper">
        <span className="canvas-search-icon">🔍</span>
        <input
          className="canvas-search-input"
          type="text"
          value={searchText}
          onChange={handleSearchChange}
          placeholder={getPlaceholder()}
          disabled={isDisabled}
        />
        {/* §14.4: Search suggestions 以 popover 展示，不新增常驻行 */}
        {showSuggestions && defaultOutputNodes.length > 0 && (
          <div className="canvas-search-popover">
            {defaultOutputNodes.map((n) => (
              <button
                key={n.entity_id}
                className="canvas-search-suggestion"
                onClick={() => handleSelectDefaultOutput(n.entity_id, n.label)}
              >
                {n.label}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="canvas-output-capsule" data-status={outputCapsule.status}>
        <span className="canvas-capsule-dot" />
        <span className="canvas-capsule-text">{getCapsuleText()}</span>
      </div>
    </div>
  );
};

export default CanvasTopSearchBar;
