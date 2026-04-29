import { Link } from 'react-router-dom';
import { TRACK_META } from '../contexts/TopicContext';
import { useAuth } from '../contexts/AuthContext';

function percent(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0%';
  return `${Math.round(value * 100)}%`;
}

export default function InsightStrip({ insights }) {
  const { user } = useAuth();
  if (!insights) return null;

  const isPaid = user?.plan && user.plan !== 'free';
  const weakest = isPaid ? (insights.weakest_concepts?.[0] || null) : null;
  const weakestTrack = weakest ? TRACK_META[weakest.track] : null;

  const streakDays = insights.streak_days || 0;
  let streakMessage;
  if (streakDays === 0) {
    streakMessage = 'Solve one question today to start a streak.';
  } else if (user?.streak_at_risk) {
    streakMessage = 'Solve one today to keep it alive.';
  } else {
    streakMessage = 'Great work! Come back tomorrow to keep it going.';
  }

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
        <p className="dashboard-insight-value">{streakDays} day{streakDays === 1 ? '' : 's'}</p>
        <p className="dashboard-insight-muted">{streakMessage}</p>
      </div>

      <div className="dashboard-insight-tile">
        <p className="dashboard-insight-kicker">Weakest concept</p>
        {!isPaid ? (
          <p className="dashboard-insight-muted">
            <Link to="/#landing-pricing" className="dashboard-insight-link">Upgrade to Pro</Link>
            {' '}to see your weakest concept and get drill recommendations.
          </p>
        ) : weakest ? (
          <>
            <p className="dashboard-insight-value">
              {weakest.concept}
              {weakestTrack ? <span className="dashboard-insight-track"> · {weakestTrack.label}</span> : null}
            </p>
            <p className="dashboard-insight-muted">
              {percent(weakest.accuracy_pct)} accuracy across {weakest.attempts} attempts
            </p>
            {weakest.summary && (
              <p className="dashboard-insight-coaching">{weakest.summary}</p>
            )}
            {weakest.recommended_path_slug ? (
              <Link
                to={`/learn/${weakest.track}/${weakest.recommended_path_slug}`}
                className="dashboard-insight-link"
              >
                Study in {weakest.recommended_path_title} →
              </Link>
            ) : (
              <Link
                to={`/practice/${weakest.track}?concepts=${encodeURIComponent(weakest.concept)}`}
                className="dashboard-insight-link"
              >
                Drill this concept →
              </Link>
            )}
            {weakest.recommended_question_ids?.[0] != null && (
              <Link
                to={`/practice/${weakest.track}/questions/${weakest.recommended_question_ids[0]}`}
                className="dashboard-insight-link dashboard-insight-link--secondary"
              >
                Practice a question →
              </Link>
            )}
          </>
        ) : (
          <p className="dashboard-insight-muted">Need at least 3 attempts on a concept to identify a weak area.</p>
        )}
      </div>
    </section>
  );
}
