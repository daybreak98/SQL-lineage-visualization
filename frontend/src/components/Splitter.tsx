import { type FC, useCallback, useRef, useState, useEffect } from 'react';

/**
 * Splitter — 8px 大热区可拖拽分隔条
 *
 * §15.3: 不保留与 Splitter 重复的布局控制按钮
 */
interface SplitterProps {
  direction: 'horizontal' | 'vertical';
  initialRatio?: number; // 左侧/上方占比 0-1
  onRatioChange?: (ratio: number) => void;
}

const Splitter: FC<SplitterProps> = ({
  direction,
  initialRatio = 0.5,
  onRatioChange,
}) => {
  const [ratio, setRatio] = useState(initialRatio);
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const handleMouseDown = useCallback(() => {
    draggingRef.current = true;
    document.body.style.cursor = direction === 'horizontal' ? 'col-resize' : 'row-resize';
    document.body.style.userSelect = 'none';
  }, [direction]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!draggingRef.current || !containerRef.current) return;
      const container = containerRef.current.parentElement;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      let newRatio: number;

      if (direction === 'horizontal') {
        newRatio = (e.clientX - rect.left) / rect.width;
      } else {
        newRatio = (e.clientY - rect.top) / rect.height;
      }

      newRatio = Math.max(0.1, Math.min(0.9, newRatio));
      setRatio(newRatio);
      onRatioChange?.(newRatio);
    };

    const handleMouseUp = () => {
      draggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [direction, onRatioChange]);

  const isHorizontal = direction === 'horizontal';

  return (
    <div
      ref={containerRef}
      className={`splitter splitter--${direction}`}
      onMouseDown={handleMouseDown}
      style={{
        [isHorizontal ? 'width' : 'height']: '8px',
        cursor: isHorizontal ? 'col-resize' : 'row-resize',
      }}
    >
      <div className="splitter-handle" />
    </div>
  );
};

export default Splitter;
