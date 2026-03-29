// Props: { output: string }
// Only renders if output is non-empty.
export default function PrintOutputPanel({ output }) {
  if (!output) return null;

  return (
    <div className="print-output">
      <div className="results-header">
        <span>Output</span>
      </div>
      <pre className="print-output-content">{output}</pre>
    </div>
  );
}
