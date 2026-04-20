import { useEffect, useMemo, useRef, useState } from 'react';

export default function ResultsTable({ columns, rows, emptyMessage = 'Query returned 0 rows.' }) {
  const scrollRef = useRef(null);
  const tableRef = useRef(null);
  const [hasOverflow, setHasOverflow] = useState(false);
  const [hiddenColumns, setHiddenColumns] = useState(0);

  const visibleColumns = useMemo(() => Math.max(columns?.length ?? 0, 0), [columns]);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return undefined;

    const updateOverflowState = () => {
      const overflow = container.scrollWidth > container.clientWidth + 1;
      setHasOverflow(overflow);
      if (!overflow) {
        setHiddenColumns(0);
        return;
      }

      const viewportRight = container.scrollLeft + container.clientWidth;
      const headerCells = tableRef.current?.querySelectorAll('thead th') ?? [];
      let remaining = 0;
      headerCells.forEach((cell) => {
        if (cell.offsetLeft + cell.offsetWidth > viewportRight + 1) {
          remaining += 1;
        }
      });
      setHiddenColumns(remaining);
    };

    const hasResizeObserver = typeof ResizeObserver !== 'undefined';
    const resizeObserver = hasResizeObserver ? new ResizeObserver(updateOverflowState) : null;
    if (resizeObserver) {
      resizeObserver.observe(container);
      if (tableRef.current) {
        resizeObserver.observe(tableRef.current);
      }
    }

    container.addEventListener('scroll', updateOverflowState, { passive: true });
    updateOverflowState();

    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      container.removeEventListener('scroll', updateOverflowState);
    };
  }, [visibleColumns, rows]);

  if (!columns || columns.length === 0) {
    return <p className="results-empty">No tabular result to display.</p>;
  }

  return (
    <>
      <div className="results-scroll" ref={scrollRef}>
        <table className="results-table" ref={tableRef}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="results-table-empty">
                  <div className="results-empty-state">
                    <span className="results-empty-label">0 rows</span>
                    <span className="results-empty-copy">{emptyMessage}</span>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} className={cell === null ? 'results-cell-null' : ''}>
                      {cell === null ? <span className="results-null-token">NULL</span> : String(cell)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {hasOverflow && hiddenColumns > 0 && (
        <div className="results-table-scroll-cue">→ {hiddenColumns} more column{hiddenColumns === 1 ? '' : 's'}</div>
      )}
    </>
  );
}
