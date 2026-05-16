import Editor from '@monaco-editor/react';

function defineForestTheme(monaco) {
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

  return (
    <Editor
      height={height}
      language={language}
      theme="forest-dark"
      value={value}
      onChange={(val) => onChange(val ?? '')}
      beforeMount={defineForestTheme}
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
