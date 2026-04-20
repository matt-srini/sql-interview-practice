import { Link } from 'react-router-dom';
import { TRACK_META } from '../contexts/TopicContext';

/**
 * Welcome-back block shown to authenticated visitors on "/".
 *
 * Replaces the marketing hero (which is for first-time visitors only).
 *
 * Props:
 *   user       — current user object (name / email)
 *   dashData   — /api/dashboard payload; used to find the last solved question
 *                and the most-active track. May be null while loading.
 */
export default function LoggedInWelcome({ user, dashData }) {
  const firstName = (user?.name || user?.email || '').split(/[\s@]/)[0] || 'there';

  const recent = dashData?.recent_activity?.[0] || null;
  const resumeTopic = recent?.topic || pickMostActiveTrack(dashData) || 'sql';
  const resumeTrackMeta = TRACK_META[resumeTopic];

  // Resume target — last solved question if known, else hub for the most-active track.
  const resumeHref = recent
    ? `/practice/${recent.topic}/questions/${recent.question_id}`
    : `/practice/${resumeTopic}`;

  const resumeKicker = recent
    ? `Last ${resumeTrackMeta?.label ?? resumeTopic}`
    : `Jump into ${resumeTrackMeta?.label ?? resumeTopic}`;

  const resumeTitle = recent?.title || (resumeTrackMeta ? `${resumeTrackMeta.label} challenge track` : 'Start practising');

  const totalSolved = dashData
    ? Object.values(dashData.tracks || {}).reduce((acc, t) => acc + (t?.solved ?? 0), 0)
    : 0;

  return (
    <section className="landing-welcome" aria-labelledby="landing-welcome-title">
      <div className="landing-welcome-inner">
        <div className="landing-welcome-heading">
          <span className="landing-kicker">Welcome back</span>
          <h1 id="landing-welcome-title" className="landing-welcome-title">
            Good to see you, {firstName}.
          </h1>
          {dashData && (
            <p className="landing-welcome-copy">
              {totalSolved > 0
                ? `${totalSolved} solved so far. Keep the streak going.`
                : 'Ready when you are — pick a track below, or jump back in.'}
            </p>
          )}
        </div>

        <div className="landing-welcome-grid">
          <Link to={resumeHref} className="landing-welcome-card landing-welcome-card--primary">
            <span className="landing-welcome-card-kicker">{resumeKicker}</span>
            <span className="landing-welcome-card-title">{resumeTitle}</span>
            <span className="landing-welcome-card-cta">
              {recent ? 'Open question →' : 'Start here →'}
            </span>
          </Link>

          <Link to="/dashboard" className="landing-welcome-card">
            <span className="landing-welcome-card-kicker">Progress</span>
            <span className="landing-welcome-card-title">Dashboard</span>
            <span className="landing-welcome-card-cta">
              See your solves →
            </span>
          </Link>

          <Link to="/mock" className="landing-welcome-card">
            <span className="landing-welcome-card-kicker">Practice under pressure</span>
            <span className="landing-welcome-card-title">Mock interview</span>
            <span className="landing-welcome-card-cta">
              Start a session →
            </span>
          </Link>
        </div>
      </div>
    </section>
  );
}

function pickMostActiveTrack(dashData) {
  if (!dashData?.tracks) return null;
  let bestTrack = null;
  let bestSolved = -1;
  for (const [topic, data] of Object.entries(dashData.tracks)) {
    const solved = data?.solved ?? 0;
    if (solved > bestSolved) {
      bestSolved = solved;
      bestTrack = topic;
    }
  }
  return bestSolved > 0 ? bestTrack : null;
}
