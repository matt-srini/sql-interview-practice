/**
 * Normalize run-code / submit API responses so the frontend always sees a
 * consistent shape, and — critically — converts Pandas dict-rows into the
 * column-ordered arrays that `ResultsTable` renders.
 *
 * Backends differ by track:
 *   - SQL returns rows as arrays-of-arrays (already ResultsTable-shaped).
 *   - Pandas returns rows as objects keyed by column name
 *     (`DataFrame.to_dict(orient="records")`), which `ResultsTable.row.map`
 *     cannot render — it expects each row to be an array of cells.
 * `dictRowsToArrays` bridges that: a no-op for array rows, a column-ordered
 * projection for object rows.
 */

export function dictRowsToArrays(columns, rows) {
  if (!Array.isArray(rows) || rows.length === 0) return rows;
  const first = rows[0];
  // Already arrays (SQL) or scalars — leave untouched.
  if (first === null || Array.isArray(first) || typeof first !== 'object') return rows;
  const cols = (Array.isArray(columns) && columns.length) ? columns : Object.keys(first);
  return rows.map((r) =>
    (r && typeof r === 'object' && !Array.isArray(r)) ? cols.map((c) => (r[c] ?? null)) : r,
  );
}

function convertBlock(block) {
  if (block && Array.isArray(block.rows)) {
    block.rows = dictRowsToArrays(block.columns, block.rows);
  }
}

/**
 * Human label for a result's row count. When the backend capped the result to a
 * display preview (truncated=true with a true total_rows), say so explicitly so
 * the user knows the full size — otherwise just the row count. Used for every
 * result panel (run + submit, SQL + pandas, practice + sample + mock).
 */
export function rowCountLabel(result) {
  const rows = result?.rows ?? [];
  if (result?.truncated && typeof result?.total_rows === 'number') {
    const shown = result.row_limit ?? rows.length;
    return `showing first ${shown} of ${result.total_rows.toLocaleString()} rows`;
  }
  return `${rows.length} row${rows.length !== 1 ? 's' : ''}`;
}

export function normalizeRunResult(data) {
  if (!data) return data;
  const d = { ...data };
  if (!('test_results' in d)) d.test_results = d.results ?? d.public_results ?? [];
  if (!('stdout' in d)) d.stdout = d.print_output ?? '';

  // Convert any DataFrame result blocks to array-rows before they reach ResultsTable.
  convertBlock(d.result);
  convertBlock(d.user_result);
  convertBlock(d.expected_result);

  if (d.result) {
    // Pandas: the nested result is authoritative for the top-level columns/rows
    // and the preview metadata (so rowCountLabel works on the top-level object).
    d.columns = d.result.columns;
    d.rows = d.result.rows;
    if (d.result.total_rows !== undefined) d.total_rows = d.result.total_rows;
    if (d.result.truncated !== undefined) d.truncated = d.result.truncated;
    if (d.result.row_limit !== undefined) d.row_limit = d.result.row_limit;
  } else {
    // SQL / others: top-level rows are already array-shaped (no-op convert).
    convertBlock(d);
  }
  return d;
}
