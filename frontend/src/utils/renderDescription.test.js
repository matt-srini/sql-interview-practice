import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { renderDescription } from './renderDescription.js';

describe('renderDescription', () => {
  it('returns null for empty/falsy input', () => {
    expect(renderDescription('')).toBeNull();
    expect(renderDescription(null)).toBeNull();
    expect(renderDescription(undefined)).toBeNull();
  });

  it('preserves numbered list steps as separate lines separated by <br> elements', () => {
    const { container } = render(
      <div>{renderDescription('1. first\n2. second\n3. third')}</div>
    );
    const brs = container.querySelectorAll('br');
    expect(brs.length).toBeGreaterThanOrEqual(2);
    const text = container.textContent;
    expect(text).toContain('first');
    expect(text).toContain('second');
    expect(text).toContain('third');
  });

  it('renders fenced code blocks as <pre> elements', () => {
    const { container } = render(
      <div>{renderDescription('Before.\n```\nSELECT 1\n```\nAfter.')}</div>
    );
    const pres = container.querySelectorAll('pre');
    expect(pres.length).toBe(1);
    expect(pres[0].textContent).toContain('SELECT 1');
    expect(container.textContent).toContain('Before.');
    expect(container.textContent).toContain('After.');
  });

  it('strips the language info-string from a language-tagged code fence', () => {
    const { container } = render(
      <div>{renderDescription('```python\nimport pandas as pd\ndf = df.copy()\n```')}</div>
    );
    const pre = container.querySelector('pre');
    expect(pre).not.toBeNull();
    expect(pre.textContent).toContain('import pandas as pd');
    expect(pre.textContent).toContain('df = df.copy()');
    // the language tag must NOT leak in as the first rendered code line
    expect(pre.textContent).not.toContain('python');
    expect(pre.textContent.trimStart().startsWith('import')).toBe(true);
  });

  it('renders inline backtick code as <code> elements', () => {
    const { container } = render(
      <div>{renderDescription('Use `GROUP BY` here.')}</div>
    );
    const codes = container.querySelectorAll('code');
    expect(codes.length).toBe(1);
    expect(codes[0].textContent).toBe('GROUP BY');
  });

  it('renders **bold** text as <strong> elements', () => {
    const { container } = render(
      <div>{renderDescription('This is **important**.')}</div>
    );
    const strongs = container.querySelectorAll('strong');
    expect(strongs.length).toBe(1);
    expect(strongs[0].textContent).toBe('important');
  });

  it('inserts a <br> for every single newline', () => {
    const { container } = render(
      <div>{renderDescription('line one\nline two\nline three')}</div>
    );
    const brs = container.querySelectorAll('br');
    // two newlines → two <br> elements
    expect(brs.length).toBe(2);
  });
});
