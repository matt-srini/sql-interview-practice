export default function SchemaViewer({ schema }) {
  if (!schema || Object.keys(schema).length === 0) return null;

  return (
    <div>
      {Object.entries(schema).map(([table, columns]) => (
        <div key={table} className="schema-table">
          <div className="schema-table-name">{table}</div>
          <ul className="schema-columns">
            {columns.map((col) => (
              <li key={col}>{col}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
