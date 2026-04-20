import { useMemo, useState } from 'react';

export default function SchemaViewer({ schema }) {
  const [search, setSearch] = useState('');
  const [copiedColumn, setCopiedColumn] = useState('');

  const schemaEntries = useMemo(() => Object.entries(schema ?? {}), [schema]);
  if (schemaEntries.length === 0) return null;

  const query = search.trim().toLowerCase();
  const filteredSchema = useMemo(() => {
    if (!query) return schemaEntries;
    return schemaEntries
      .map(([table, columns]) => {
        const tableMatch = table.toLowerCase().includes(query);
        if (tableMatch) return [table, columns];
        const matchingColumns = columns.filter((col) => col.toLowerCase().includes(query));
        return [table, matchingColumns];
      })
      .filter(([, columns]) => columns.length > 0);
  }, [schemaEntries, query]);

  const handleCopyColumn = async (column) => {
    try {
      await navigator.clipboard.writeText(column);
      setCopiedColumn(column);
      window.setTimeout(() => setCopiedColumn(''), 1200);
    } catch {
      // Clipboard failures are non-fatal in constrained browser contexts.
    }
  };

  return (
    <div className="schema-viewer-wrap">
      <input
        type="text"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        className="schema-search-input"
        placeholder="Search table or column"
        aria-label="Search table or column"
      />
      <div className="schema-viewer">
        {filteredSchema.map(([table, columns]) => (
          <div key={table} className="schema-table">
            <div className="schema-table-header">
              <div className="schema-table-name">{table}</div>
              <div className="schema-table-count">{columns.length} cols</div>
            </div>
            <ul className="schema-columns">
              {columns.map((col) => (
                <li key={col}>
                  <button
                    type="button"
                    className={`schema-column-token schema-column-copy${copiedColumn === col ? ' is-copied' : ''}`}
                    onClick={() => handleCopyColumn(col)}
                    title={`Copy ${col}`}
                  >
                    {col}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {filteredSchema.length === 0 && (
          <p className="schema-search-empty">No tables or columns match your search.</p>
        )}
      </div>
    </div>
  );
}
