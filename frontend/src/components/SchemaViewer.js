export default function SchemaViewer({ schema }) {
  if (!schema || Object.keys(schema).length === 0) return null;

  return (
    <div className="schema-viewer">
      {Object.entries(schema).map(([table, columns]) => (
        <div key={table} className="schema-table">
          <div className="schema-table-header">
            <div className="schema-table-name">{table}</div>
            <div className="schema-table-count">{columns.length} cols</div>
          </div>
          <ul className="schema-columns">
            {columns.map((col) => (
              <li key={col}>
                <span className="schema-column-token">{col}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
