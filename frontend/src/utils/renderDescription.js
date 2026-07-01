import { Fragment } from 'react';

/**
 * Render a question description string that may contain:
 *   - Fenced code blocks (```...```)
 *   - Markdown tables (| a | b |\n|---|---|\n| 1 | 2 |)
 *   - Inline backtick code (`...`)
 *   - Bold text (**...**)
 *   - Paragraph breaks (\n\n)
 *
 * Returns an array of React nodes for rendering inside a block container (<div>) —
 * output can include <pre> and <table> blocks, which are invalid inside <p>.
 */

const isTableRow = (l) => /^\s*\|.*\|\s*$/.test(l);
const isTableSep = (l) => {
  const t = l.trim();
  return /^[\s|:-]+$/.test(t) && t.includes('-') && t.includes('|');
};
const splitCells = (l) =>
  l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());

// Inline markup (backtick code + **bold**) within a single string.
function renderInline(text, keyPrefix) {
  const segments = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return segments.map((seg, j) => {
    if (seg.startsWith('`') && seg.endsWith('`')) {
      return <code key={`${keyPrefix}-c${j}`} className="description-inline-code">{seg.slice(1, -1)}</code>;
    }
    if (seg.startsWith('**') && seg.endsWith('**')) {
      return <strong key={`${keyPrefix}-b${j}`}>{seg.slice(2, -2)}</strong>;
    }
    return seg;
  });
}

// A run of non-table text: inline markup with every \n becoming a <br>.
function renderTextRun(text, keyPrefix) {
  const out = [];
  renderInline(text, keyPrefix).forEach((seg, j) => {
    if (typeof seg === 'string') {
      const lines = seg.split('\n');
      lines.forEach((line, k) => {
        if (line) out.push(line);
        if (k < lines.length - 1) out.push(<br key={`${keyPrefix}-br${j}-${k}`} />);
      });
    } else {
      out.push(seg);
    }
  });
  return out;
}

export function renderDescription(text) {
  if (!text) return null;
  if (typeof text !== 'string') text = String(text);
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith('```') && part.endsWith('```')) {
      const inner = part.slice(3, -3);
      // Drop the opening fence's info string (language id, e.g. ```python) — it is
      // the remainder of the first line — and a single trailing newline before the
      // closing fence, so neither leaks into the rendered <code>.
      const code = inner.replace(/^[^\n]*\n/, '').replace(/\n$/, '');
      return (
        <pre key={i} className="description-code-block">
          <code>{code}</code>
        </pre>
      );
    }
    // Non-code part: segment into markdown-table blocks and text runs.
    const lines = part.split('\n');
    const blocks = [];
    let buf = [];
    const flush = () => {
      if (buf.length) { blocks.push({ type: 'text', text: buf.join('\n') }); buf = []; }
    };
    for (let li = 0; li < lines.length; li++) {
      if (isTableRow(lines[li]) && li + 1 < lines.length && isTableSep(lines[li + 1])) {
        flush();
        const header = splitCells(lines[li]);
        const body = [];
        let lj = li + 2;
        while (lj < lines.length && isTableRow(lines[lj])) { body.push(splitCells(lines[lj])); lj++; }
        blocks.push({ type: 'table', header, body });
        li = lj - 1;
      } else {
        buf.push(lines[li]);
      }
    }
    flush();

    const nodes = blocks.map((blk, bi) => {
      if (blk.type === 'table') {
        return (
          <div key={`tbl-${i}-${bi}`} className="description-table-wrap">
            <table className="description-table">
              <thead>
                <tr>{blk.header.map((c, ci) => <th key={ci}>{renderInline(c, `th${i}-${bi}-${ci}`)}</th>)}</tr>
              </thead>
              <tbody>
                {blk.body.map((row, ri) => (
                  <tr key={ri}>{row.map((c, ci) => <td key={ci}>{renderInline(c, `td${i}-${bi}-${ri}-${ci}`)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      return <span key={`txt-${i}-${bi}`}>{renderTextRun(blk.text, `txt${i}-${bi}`)}</span>;
    });
    return <Fragment key={i}>{nodes}</Fragment>;
  });
}
