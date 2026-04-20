import { Link } from 'react-router-dom';
import { TRACK_META } from '../contexts/TopicContext';

function percent(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0%';
  return `${Math.round(value * 100)}%`;
}

export default function InsightStrip({ insights }) {
  if (!insights) return null;

  const weakest = insights.weakest_concepts?.[0] || null;
  const weakestTrack = weakest ? TRACK_META[weakest.track] : null;

  return (
    <section className="dashboard-section dashboard-insight-strip" aria-label="Performance insights">
      <div className="dashboard-insight-tile">
        <p className="dashboard-insight-kicker">Cross-track coaching</p>
        <p className="dashboard-insight-copy">
          {insights.cross_track_insight || 'Keep solving across tracks to unlock personalized pace coaching.'}
        </p>
      </div>

      <div className="dashboard-insight-tile">
        <p className="dashboard-insight-kicker">Current streak</p>
        <p className="dashboard-insight-value">{insights.streak_days || 0} day{insights.streak_days === 1 ? '' : 's'}</p>
        <p className="dashboard-insight-muted">
          {insights.streak_days > 0 ? 'Solve one today to keep it alive.' : 'Solve one question today to start a streak.'}
        </p>
      </div>

      <div className="dashboard-insight-tile">
        <p className="dashboard-insight-kicker">Weakest concept</p>
        {weakest ? (
          <>
            <p className="dashboard-insight-value">
              {weakest.concept}
              {weakestTrack ? <span className="dashboard-insight-track"> · {weakestTrack.label}</span> : null}
            </p>
            <p className="dashboard-insight-muted">
              {percent(weakest.accuracy_pct)} accuracy across {weakest.attempts} attempts
            </p>
            <Link
              to={`/practice/${weakest.track}?concepts=${encodeURIComponent(weakest.concept)}`}
              className="dashboard-insight-link"
            >
              Drill this concept →
            </Link>
          </>
        ) : (
          <p className="dashboard-insight-muted">Need at least 3 attempts on a concept to identify a weak area.</p>
        )}
      </div>
    </section>
  );
}
