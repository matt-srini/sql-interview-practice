import Editor from '@monaco-editor/react';

export default function SQLEditor({ value, onChange, height = '340px' }) {
  return (
    <Editor
      height={height}
      language="sql"
      theme="vs-dark"
      value={value}
      onChange={(val) => onChange(val ?? '')}
      options={{
        minimap: { enabled: false },
        fontSize: 14,
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
