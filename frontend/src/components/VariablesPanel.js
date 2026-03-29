// Props:
//   dataframes: { df_users: 'users.csv', df_orders: 'orders.csv', ... }
//   schema: { df_users: ['user_id', 'email', ...], ... }
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
                <span className="variable-source">{csvFile}</span>
              </div>
              {cols.length > 0 && (
                <div className="variable-columns">
                  {cols.map((col) => (
                    <span key={col} className="variable-column-token">{col}</span>
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
