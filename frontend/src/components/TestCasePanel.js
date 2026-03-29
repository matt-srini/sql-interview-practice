// Props:
//   results: Array<{ input, expected, actual, passed, stdout, error }>
//   hiddenSummary: { passed: number, total: number } | null
export default function TestCasePanel({ results = [], hiddenSummary = null }) {
  if (!results.length && !hiddenSummary) return null;

  return (
    <div className="test-case-panel">
      <div className="results-header">
        <span>Test Cases</span>
        <span>
          {results.filter((r) => r.passed).length}/{results.length} public
          {hiddenSummary ? ` · ${hiddenSummary.passed}/${hiddenSummary.total} hidden` : ''}
        </span>
      </div>

      <div className="test-case-list">
        {results.map((tc, i) => (
          <div key={i} className={`test-case-row ${tc.passed ? 'test-case-row--pass' : 'test-case-row--fail'}`}>
            <div className="test-case-status" aria-label={tc.passed ? 'Passed' : 'Failed'}>
              {tc.passed ? '✓' : '✗'}
            </div>
            <div className="test-case-body">
              <div className="test-case-fields">
                <div className="test-case-field">
                  <span className="test-case-label">Input</span>
                  <code className="test-case-value">{String(tc.input)}</code>
                </div>
                <div className="test-case-field">
                  <span className="test-case-label">Expected</span>
                  <code className="test-case-value">{String(tc.expected)}</code>
                </div>
                {!tc.passed && (
                  <div className="test-case-field">
                    <span className="test-case-label">Got</span>
                    <code className="test-case-value test-case-value--wrong">{String(tc.actual)}</code>
                  </div>
                )}
              </div>
              {tc.stdout && (
                <div className="test-case-stdout">
                  <span className="test-case-label">stdout</span>
                  <pre className="test-case-stdout-content">{tc.stdout}</pre>
                </div>
              )}
              {tc.error && (
                <div className="test-case-error">
                  <span className="test-case-label">Error</span>
                  <pre className="test-case-error-content">{tc.error}</pre>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {hiddenSummary && (
        <div className="test-case-hidden-summary">
          Hidden tests: {hiddenSummary.passed}/{hiddenSummary.total} passed
        </div>
      )}
    </div>
  );
}
