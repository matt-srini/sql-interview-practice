export default function ResultsTable({ columns, rows, emptyMessage = 'Query returned 0 rows.' }) {
  if (!columns || columns.length === 0) {
    return <p className="results-empty">No tabular result to display.</p>;
  }

  return (
    <div className="results-scroll">
      <table className="results-table">
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
  );
}
