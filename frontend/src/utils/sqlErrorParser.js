const HINTS = [
  {
    pattern: /no such table|table .* does not exist/i,
    userMessage: 'A referenced table was not found. Double-check table names in the schema panel.',
  },
  {
    pattern: /no such column|column .* does not exist|binder error/i,
    userMessage: 'A referenced column was not found. Verify column names and aliases.',
  },
  {
    pattern: /syntax error|parser error/i,
    userMessage: 'SQL syntax error. Check commas, parentheses, and clause order.',
  },
  {
    pattern: /group by/i,
    userMessage: 'GROUP BY mismatch. Ensure non-aggregated selected columns are grouped.',
  },
  {
    pattern: /ambiguous/i,
    userMessage: 'Ambiguous column reference. Prefix the column with a table alias.',
  },
  {
    pattern: /division by zero/i,
    userMessage: 'Division by zero occurred. Use NULLIF or a safe denominator check.',
  },
  {
    pattern: /scalar function with name to_char does not exist/i,
    userMessage: "DuckDB doesn't have TO_CHAR — use STRFTIME('%Y-%m', date) for date formatting.",
  },
  {
    pattern: /scalar function with name \w+ does not exist/i,
    userMessage: 'Unknown function — this platform runs DuckDB, which differs from Postgres/MySQL in some built-ins. Visit the SQL track page for a syntax reference.',
  },
];

export function parseSqlError(errorText) {
  const raw = String(errorText || '').trim();
  if (!raw) return null;

  const lineMatch = raw.match(/line\s+(\d+)/i);
  const linePart = lineMatch ? ` (line ${lineMatch[1]})` : '';

  const matched = HINTS.find((hint) => hint.pattern.test(raw));
  if (!matched) return raw;

  return `${matched.userMessage}${linePart}`;
}
