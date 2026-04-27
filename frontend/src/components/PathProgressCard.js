import { Link } from 'react-router-dom';
import { TRACK_META } from '../contexts/TopicContext';

export default function PathProgressCard({ path, compact = false }) {
  const meta = TRACK_META[path.topic] || TRACK_META['sql'];
  const pct = path.question_count > 0 ? (path.solved_count / path.question_count) * 100 : 0;
  const started = path.solved_count > 0;
  const isPro = path.tier === 'pro';
  const isFreeStarter = path.tier === 'free' && path.role === 'starter';
  const isFreeIntermediate = path.tier === 'free' && path.role === 'intermediate';

  return (
    <Link
      to={`/learn/${path.topic}/${path.slug}`}
      className={`path-card${compact ? ' path-card--compact' : ''}${isPro && !path.accessible ? ' path-card--pro' : ''}`}
    >
      <div className="path-card-header">
        <span className="path-card-dot" style={{ background: meta.color }} />
        <span className="path-card-topic">{meta.label}</span>
        {isPro && <span className="path-card-tier-badge">Pro</span>}
        {isFreeStarter && <span className="path-card-tier-badge path-card-tier-badge--free">Included with Free</span>}
        {isFreeIntermediate && <span className="path-card-tier-badge path-card-tier-badge--free">Included with Free</span>}
      </div>
      <div className="path-card-title">{path.title}</div>
      {!compact && <div className="path-card-desc">{path.description}</div>}
      <div className="path-card-meta">{path.question_count} questions</div>
      <div className="path-card-progress">
        <div className="path-card-progress-bar">
          <div
            className="path-card-progress-fill"
            style={{ width: `${pct}%`, background: meta.color }}
          />
        </div>
        <span className="path-card-progress-label">
          {path.solved_count}/{path.question_count}
        </span>
      </div>
      <div className="path-card-cta">
        {isPro && !path.accessible ? 'Unlock with Pro →' : started ? 'Continue →' : 'Start path →'}
      </div>
    </Link>
  );
}
