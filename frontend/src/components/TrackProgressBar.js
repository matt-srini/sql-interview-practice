import { useEffect, useState } from 'react';

// Props:
//   solved: number
//   total: number
//   color?: string   (CSS color value)
//   showLabel?: boolean
export default function TrackProgressBar({ solved = 0, total = 0, color, showLabel = true }) {
  const pct = total > 0 ? Math.round((solved / total) * 100) : 0;
  const [animatedPct, setAnimatedPct] = useState(0);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setAnimatedPct(pct));
    return () => window.cancelAnimationFrame(frame);
  }, [pct]);

  return (
    <div className="track-progress-bar-wrap">
      <div className="track-progress-bar-track">
        <div
          className="track-progress-bar-fill"
          style={{ width: `${animatedPct}%`, background: color || 'var(--accent)' }}
          role="progressbar"
          aria-valuenow={solved}
          aria-valuemin={0}
          aria-valuemax={total}
        />
      </div>
      {showLabel && (
        <span className="track-progress-bar-label">
          {solved} / {total}
        </span>
      )}
    </div>
  );
}
