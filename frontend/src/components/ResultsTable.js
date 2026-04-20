import { useEffect, useMemo, useRef, useState } from 'react';

/**
 * Props:
 *   columns          Column name array
 *   rows             Row data (array of arrays)
 *   emptyMessage     Message shown when rows is empty
 *   diffMode         When true, highlight cells that differ from expected
 *   expectedColumns  Column names of the reference result (for diff)
 *   expectedRows     Row data of the reference result (for diff)
 */
export default function ResultsTable({
  columns,
  rows,
  emptyMessage = 'Query returned 0 rows.',
  diffMode = false,
  expectedColumns = null,
  expectedRows = null,
}) {
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

  // Build cell-level diff data when diffMode is enabled
  const diffData = useMemo(() => {
    if (!diffMode || !expectedRows || !expectedColumns || !columns || !rows) return null;

    // Map: normalised expected column name → index in expectedColumns
    const expectedColByName = new Map();
    expectedColumns.forEach((col, i) => expectedColByName.set(String(col).toLowerCase(), i));

    // For each user column, find the matching expected column index (-1 if absent)
    const colMapping = columns.map((col) => {
      const idx = expectedColByName.get(String(col).toLowerCase());
      return idx !== undefined ? idx : -1;
    });

    const sharedCount = Math.min(rows.length, expectedRows.length);

    // Statuses: 'match' | 'mismatch' | 'no-col' | 'extra'
    const cellStatus = rows.map((row, r) => {
      if (r >= sharedCount) return row.map(() => 'extra');
      return row.map((cell, c) => {
        const expColIdx = colMapping[c];
        if (expColIdx === -1) return 'no-col';
        const expCell = expectedRows[r][expColIdx];
        const userStr = cell === null ? 'null' : String(cell);
        const expStr = expCell === null ? 'null' : String(expCell);
        return userStr === expStr ? 'match' : 'mismatch';
      });
    });

    const mismatchCount = cellStatus.flat().filter((s) => s === 'mismatch' || s === 'no-col').length;
    const extraRows = Math.max(0, rows.length - expectedRows.length);
    const missingRows = Math.max(0, expectedRows.length - rows.length);

    return { cellStatus, mismatchCount, extraRows, missingRows };
  }, [diffMode, columns, rows, expectedColumns, expectedRows]);

  if (!columns || columns.length === 0) {
    return <p className="results-empty">No tabular result to display.</p>;
  }

  return (
    <>
      {diffData && (diffData.mismatchCount > 0 || diffData.extraRows > 0 || diffData.missingRows > 0) && (
        <div className="diff-summary">
          {diffData.mismatchCount > 0 && (
            <span className="diff-summary-item diff-summary-mismatch">
              {diffData.mismatchCount} cell{diffData.mismatchCount !== 1 ? 's' : ''} differ
            </span>
          )}
          {diffData.extraRows > 0 && (
            <span className="diff-summary-item diff-summary-extra">
              +{diffData.extraRows} extra row{diffData.extraRows !== 1 ? 's' : ''}
            </span>
          )}
          {diffData.missingRows > 0 && (
            <span className="diff-summary-item diff-summary-missing">
              −{diffData.missingRows} missing row{diffData.missingRows !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}
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
              rows.map((row, i) => {
                const rowStatuses = diffData?.cellStatus[i];
                const isExtraRow = rowStatuses?.[0] === 'extra';
                return (
                  <tr key={i} className={isExtraRow ? 'row-diff-extra' : undefined}>
                    {row.map((cell, j) => {
                      const cellSt = rowStatuses?.[j];
                      const cellClass = [
                        cell === null ? 'results-cell-null' : '',
                        cellSt === 'mismatch' || cellSt === 'no-col' ? 'cell-diff-mismatch' : '',
                        cellSt === 'match' ? 'cell-diff-match' : '',
                        cellSt === 'extra' ? 'cell-diff-extra' : '',
                      ].filter(Boolean).join(' ') || undefined;
                      return (
                        <td key={j} className={cellClass}>
                          {cell === null ? <span className="results-null-token">NULL</span> : String(cell)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
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
