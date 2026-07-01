// Props:
//   dataframes: { df_users: 'users.csv', df_orders: 'orders.csv', ... }
//   schema: { df_users: ['user_id', 'email', ...], ... }

// Defensive: schema columns and dataframe values should be strings, but a malformed
// question could deliver an object — rendering one directly crashes React. Coerce safely.
function asText(v) {
  if (typeof v === 'string' || typeof v === 'number') return v;
  if (v == null) return '';
  if (typeof v === 'object') return v.name ?? v.column ?? v.label ?? JSON.stringify(v);
  return String(v);
}

export default function VariablesPanel({ dataframes = {}, schema = {} }) {
  const entries = Object.entries(dataframes);
  if (!entries.length) return null;

  return (
    <div className="card variables-panel">
      <div className="section-heading">
        <div>
          <h3>Available DataFrames</h3>
        </div>
        <span className="section-meta">{entries.length} vars</span>
      </div>

      <div className="variables-list">
        {entries.map(([varName, csvFile]) => {
          const cols = schema[varName] ?? [];
          return (
            <div key={varName} className="variable-row">
              <div className="variable-header">
                <code className="variable-name">{varName}</code>
                <span className="variable-source">{asText(csvFile)}</span>
              </div>
              {cols.length > 0 && (
                <div className="variable-columns">
                  {cols.map((col) => (
                    <span key={String(col)} className="variable-column-token">{asText(col)}</span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
