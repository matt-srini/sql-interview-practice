import Editor from '@monaco-editor/react';

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
export default function CodeEditor({ value, onChange, language = 'sql', height = '340px', fontSize = 14, onMount }) {
  return (
    <Editor
      height={height}
      language={language}
      theme="vs-dark"
      value={value}
      onChange={(val) => onChange(val ?? '')}
      onMount={onMount}
      options={{
        minimap: { enabled: false },
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
