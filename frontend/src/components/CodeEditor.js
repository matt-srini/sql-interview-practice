import Editor from '@monaco-editor/react';
import { useTheme } from '../App';

// Two editor themes. 'forest-dark' is the original green-tinted editor, kept for
// LIGHT page mode (the praised warm two-tone island on paper). 'charcoal-dark' is a
// neutral charcoal editor used under DARK pages, so the editor matches the muted
// charcoal theme instead of being the lone green environment in an otherwise calm
// dark UI (2026-06-17; see docs/decisions/DECISIONS.md editor_charcoal_dark — this
// supersedes the editor sub-decision of the 2026-06-12 charcoal entry). Syntax colors
// (vs-dark base) are shared; only the chrome — bg / gutter / line / indent — differs.
function defineEditorThemes(monaco) {
  monaco.editor.defineTheme('forest-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#0F2218',
      'editor.lineHighlightBackground': '#152D1E',
      'editorLineNumber.foreground': '#4A7060',
      'editorLineNumber.activeForeground': '#7AAE90',
      'editorIndentGuide.background': '#1E3828',
      'editorIndentGuide.activeBackground': '#2A4A38',
    },
  });
  monaco.editor.defineTheme('charcoal-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [],
    colors: {
      'editor.background': '#16181C',
      'editor.lineHighlightBackground': '#212327',
      'editorLineNumber.foreground': '#6E747D',
      'editorLineNumber.activeForeground': '#9BA1A9',
      'editorIndentGuide.background': '#282A2E',
      'editorIndentGuide.activeBackground': '#474C54',
    },
  });
}

/**
 * Language-agnostic Monaco editor wrapper.
 *
 * Props:
 *   value        Current editor content
 *   onChange     Called with new content on every keystroke
 *   language     Monaco language id — 'sql' | 'python' (default: 'sql')
 *   height       CSS height string passed to Monaco (default: '340px')
 *   fontSize     Editor font size in px (default: 14)
 *   onMount      Optional (editor, monaco) callback forwarded to Monaco's onMount.
 *                Use this to register keyboard commands via editor.addCommand().
 */
export default function CodeEditor({
  value,
  onChange,
  language = 'sql',
  height = '340px',
  fontSize = 14,
  onMount,
  ariaLabel,
}) {
  const resolvedAriaLabel = ariaLabel || `${language === 'python' ? 'Python' : 'SQL'} code editor`;
  // Editor is always dark, but matches the page theme's flavor: forest under light
  // pages, charcoal under dark pages. (|| {} guards isolated renders without the provider.)
  const { isDark } = useTheme() || {};

  return (
    <Editor
      height={height}
      language={language}
      theme={isDark ? 'charcoal-dark' : 'forest-dark'}
      value={value}
      onChange={(val) => onChange(val ?? '')}
      beforeMount={defineEditorThemes}
      onMount={onMount}
      options={{
        minimap: { enabled: false },
        ariaLabel: resolvedAriaLabel,
        fontSize,
        fontFamily: '"JetBrains Mono", "SFMono-Regular", Consolas, monospace',
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        tabSize: 2,
        automaticLayout: true,
        padding: { top: 14, bottom: 14 },
      }}
    />
  );
}
