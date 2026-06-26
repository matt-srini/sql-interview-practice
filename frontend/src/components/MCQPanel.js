// Props:
//   options: string[]
//   selectedOption: number | null
//   onSelect: (index: number) => void
//   submitted: boolean
//   canReselect: boolean          (when true, options stay clickable after submit — Model B re-attempt after reveal)
//   correct: boolean | null
//   correctIndex: number | null   (revealed after submit)
//   explanation: string
//   locked: boolean               (when true, renders locked placeholder instead of options)
export default function MCQPanel({
  options = [],
  selectedOption,
  onSelect,
  submitted,
  canReselect = false,
  correct,
  correctIndex,
  explanation,
  locked = false,
  explanationLabel = 'Explanation',
  lockedCopy = 'Unlock to see response options and reasoning',
}) {
  if (locked) {
    return (
      <div className="mcq-panel">
        <div className="mcq-locked">
          <span className="mcq-locked-icon" aria-hidden="true">&#8855;</span>
          <p className="mcq-locked-copy">{lockedCopy}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mcq-panel">
      <div className="mcq-options">
        {options.map((option, i) => {
          let cls = 'mcq-option';
          if (selectedOption === i) cls += ' mcq-option--selected';
          if (submitted && !canReselect && correctIndex !== null && correctIndex === i) cls += ' mcq-option--correct';
          if (submitted && !canReselect && selectedOption === i && !correct) cls += ' mcq-option--wrong';

          return (
            <button
              key={i}
              className={cls}
              onClick={() => (!submitted || canReselect) && onSelect(i)}
              disabled={submitted && !canReselect}
              aria-pressed={selectedOption === i}
            >
              <span className="mcq-option-letter">{String.fromCharCode(65 + i)}</span>
              <span className="mcq-option-text">{option}</span>
              {submitted && !canReselect && correctIndex !== null && correctIndex === i && (
                <span className="mcq-option-icon mcq-option-icon--correct" aria-label="Correct">✓</span>
              )}
              {submitted && !canReselect && selectedOption === i && !correct && (
                <span className="mcq-option-icon mcq-option-icon--wrong" aria-label="Wrong">✗</span>
              )}
            </button>
          );
        })}
      </div>

      {submitted && explanation && (
        <div className="mcq-explanation">
          <div className="mcq-explanation-label">{explanationLabel}</div>
          <p>{explanation}</p>
        </div>
      )}
    </div>
  );
}
