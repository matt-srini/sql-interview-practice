// Props:
//   options: string[]
//   selectedOption: number | null
//   onSelect: (index: number) => void
//   submitted: boolean
//   correct: boolean | null
//   correctIndex: number | null   (revealed after submit)
//   explanation: string
export default function MCQPanel({
  options = [],
  selectedOption,
  onSelect,
  submitted,
  correct,
  correctIndex,
  explanation,
}) {
  return (
    <div className="mcq-panel">
      <div className="mcq-options">
        {options.map((option, i) => {
          let cls = 'mcq-option';
          if (selectedOption === i) cls += ' mcq-option--selected';
          if (submitted && correctIndex !== null && correctIndex === i) cls += ' mcq-option--correct';
          if (submitted && selectedOption === i && !correct) cls += ' mcq-option--wrong';

          return (
            <button
              key={i}
              className={cls}
              onClick={() => !submitted && onSelect(i)}
              disabled={submitted}
              aria-pressed={selectedOption === i}
            >
              <span className="mcq-option-letter">{String.fromCharCode(65 + i)}</span>
              <span className="mcq-option-text">{option}</span>
              {submitted && correctIndex !== null && correctIndex === i && (
                <span className="mcq-option-icon mcq-option-icon--correct" aria-label="Correct">✓</span>
              )}
              {submitted && selectedOption === i && !correct && (
                <span className="mcq-option-icon mcq-option-icon--wrong" aria-label="Wrong">✗</span>
              )}
            </button>
          );
        })}
      </div>

      {submitted && explanation && (
        <div className="mcq-explanation">
          <div className="mcq-explanation-label">Explanation</div>
          <p>{explanation}</p>
        </div>
      )}
    </div>
  );
}
