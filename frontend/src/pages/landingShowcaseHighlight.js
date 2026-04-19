import { Fragment } from 'react';

const KW = {
  sql: new Set([
    'SELECT','FROM','WHERE','GROUP','BY','ORDER','HAVING','JOIN','LEFT','RIGHT','INNER','OUTER','ON','AS',
    'AND','OR','NOT','IN','IS','NULL','CASE','WHEN','THEN','ELSE','END','WITH','OVER','PARTITION','ROWS',
    'RANGE','BETWEEN','PRECEDING','FOLLOWING','CURRENT','ROW','UNBOUNDED','DESC','ASC','LIMIT','DISTINCT','UNION',
  ]),
  python: new Set([
    'def','return','if','elif','else','for','while','in','not','and','or','is','None','True','False',
    'import','from','as','class','lambda','pass','break','continue','try','except','finally','raise','with','yield',
  ]),
  markdown: new Set([]),
};

const COMMENT = { sql: '--', python: '#', markdown: '#' };

function tokenizeLine(line, language, keySeed) {
  const parts = [];
  let key = keySeed;
  let i = 0;
  const comment = COMMENT[language];
  // comment: whole-line or trailing
  const cmtIdx = line.indexOf(comment);
  let codePart = line;
  let cmtPart = '';
  if (cmtIdx !== -1) {
    // ignore if inside a string — crude check: count quotes before cmtIdx
    const pre = line.slice(0, cmtIdx);
    const oddQuotes = (pre.match(/'/g) || []).length % 2 === 1 || (pre.match(/"/g) || []).length % 2 === 1;
    if (!oddQuotes) {
      codePart = line.slice(0, cmtIdx);
      cmtPart = line.slice(cmtIdx);
    }
  }

  // regex order: strings, numbers, functions, keywords, identifiers
  const stringRe = /'([^'\\]|\\.)*'|"([^"\\]|\\.)*"/g;
  const numRe = /\b\d+(?:\.\d+)?\b/g;
  const wordRe = /[A-Za-z_][A-Za-z0-9_]*/g;

  // Build a merged span list by scanning sequentially
  const tokens = [];
  while (i < codePart.length) {
    stringRe.lastIndex = i;
    numRe.lastIndex = i;
    wordRe.lastIndex = i;
    const sM = stringRe.exec(codePart);
    const nM = numRe.exec(codePart);
    const wM = wordRe.exec(codePart);
    const candidates = [
      sM && sM.index >= i ? { type: 'str', m: sM } : null,
      nM && nM.index >= i ? { type: 'num', m: nM } : null,
      wM && wM.index >= i ? { type: 'word', m: wM } : null,
    ].filter(Boolean);
    if (!candidates.length) {
      tokens.push({ type: 'txt', text: codePart.slice(i) });
      break;
    }
    candidates.sort((a, b) => a.m.index - b.m.index);
    const next = candidates[0];
    if (next.m.index > i) tokens.push({ type: 'txt', text: codePart.slice(i, next.m.index) });
    const text = next.m[0];
    if (next.type === 'word') {
      const upper = text.toUpperCase();
      const isKw = language === 'sql'
        ? KW.sql.has(upper)
        : (KW[language] && KW[language].has(text));
      // function call if followed immediately by `(`
      const after = codePart[next.m.index + text.length];
      if (isKw) tokens.push({ type: 'kw', text });
      else if (after === '(') tokens.push({ type: 'fn', text });
      else tokens.push({ type: 'txt', text });
    } else {
      tokens.push({ type: next.type, text });
    }
    i = next.m.index + text.length;
  }
  if (cmtPart) tokens.push({ type: 'com', text: cmtPart });

  const cls = { kw: 'tok-kw', str: 'tok-str', num: 'tok-num', fn: 'tok-fn', com: 'tok-com' };
  tokens.forEach((t) => {
    if (t.type === 'txt') parts.push(t.text);
    else parts.push(<span key={`t${key++}`} className={cls[t.type]}>{t.text}</span>);
  });
  return { parts, nextKey: key };
}

export function highlightCode(code, language) {
  const lines = code.split('\n');
  const out = [];
  let key = 0;
  lines.forEach((line, li) => {
    const { parts, nextKey } = tokenizeLine(line, language, key);
    key = nextKey;
    out.push(
      <Fragment key={`l${li}`}>
        {parts}
        {li < lines.length - 1 ? '\n' : null}
      </Fragment>
    );
  });
  return out;
}
