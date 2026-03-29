import CodeEditor from './CodeEditor';

// Backward-compatible wrapper — always uses SQL language
export default function SQLEditor({ value, onChange, height = '340px' }) {
  return <CodeEditor value={value} onChange={onChange} language="sql" height={height} />;
}
