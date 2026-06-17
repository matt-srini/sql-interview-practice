/**
 * CodeEditor theme-awareness (2026-06-17).
 *
 * The editor is always dark, but matches the page theme's flavor:
 *   - light page → 'forest-dark'   (#0F2218)
 *   - dark page  → 'charcoal-dark'  (#16181C)
 * Guards the useTheme().isDark → Monaco `theme` prop switch, plus the no-provider
 * fallback (|| {}). Monaco can't render in jsdom, so we mock it to capture the prop.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';

const state = vi.hoisted(() => ({ isDark: false, returnNull: false, capturedTheme: null }));

vi.mock('@monaco-editor/react', () => ({
  default: (props) => { state.capturedTheme = props.theme; return null; },
}));
// Control isDark without importing the real App.js route tree.
vi.mock('../App', () => ({
  useTheme: () => (state.returnNull ? null : { isDark: state.isDark }),
}));

import CodeEditor from './CodeEditor';

afterEach(() => { cleanup(); state.capturedTheme = null; state.returnNull = false; });

describe('CodeEditor theme', () => {
  it('uses forest-dark under light pages', () => {
    state.isDark = false;
    render(<CodeEditor value="" onChange={() => {}} />);
    expect(state.capturedTheme).toBe('forest-dark');
  });

  it('uses charcoal-dark under dark pages', () => {
    state.isDark = true;
    render(<CodeEditor value="" onChange={() => {}} />);
    expect(state.capturedTheme).toBe('charcoal-dark');
  });

  it('falls back to forest-dark when no theme provider is present', () => {
    state.returnNull = true;
    render(<CodeEditor value="" onChange={() => {}} />);
    expect(state.capturedTheme).toBe('forest-dark');
  });
});
