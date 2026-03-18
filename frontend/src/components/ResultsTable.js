export default function ResultsTable({ columns, rows }) {
  if (!columns || columns.length === 0) {
    return <p className="results-empty">No results to display.</p>;
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
              <td colSpan={columns.length} style={{ textAlign: 'center', color: '#64748b' }}>
                Query returned 0 rows.
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>{cell === null ? <span style={{ color: '#64748b' }}>NULL</span> : String(cell)}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
