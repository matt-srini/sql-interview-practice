import { NavLink } from 'react-router-dom';
import { useTopic } from '../contexts/TopicContext';

function titleCase(value) {
  if (!value) return '';
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function DifficultyHeader({ difficulty, counts, collapsed, onToggle }) {
  return (
    <button className="sidebar-group-header" onClick={onToggle} aria-expanded={!collapsed}>
      <div className="sidebar-group-title">
        <span className={`badge badge-${difficulty}`}>{difficulty}</span>
        <div className="sidebar-group-copy">
          <span className="sidebar-group-name">{titleCase(difficulty)}</span>
          <span className="sidebar-group-meta">{counts.solved} solved · {counts.total} total</span>
        </div>
      </div>
      <div className="sidebar-group-summary">
        <span className="sidebar-group-count">
          {counts.solved}/{counts.total}
        </span>
        <span className="sidebar-chevron">{collapsed ? '▸' : '▾'}</span>
      </div>
    </button>
  );
}

function QuestionStateLabel({ q, isActive = false }) {
  if (isActive) {
    return <span className="sidebar-question-label sidebar-question-label-current">Current</span>;
  }

  if (q.state === 'solved') {
    return <span className="sidebar-question-label sidebar-question-label-solved">Solved</span>;
  }

  if (q.state === 'locked') {
    return <span className="sidebar-question-label sidebar-question-label-locked">Locked</span>;
  }

  if (q.is_next) {
    return <span className="sidebar-question-label sidebar-question-label-next">Next</span>;
  }

  return null;
}

function QuestionContent({ q, isActive = false }) {
  const orderState = isActive ? 'current' : q.state === 'solved' ? 'solved' : q.state === 'locked' ? 'locked' : q.is_next ? 'next' : 'open';

  return (
    <>
      <div className="sidebar-question-leading">
        <span className={`sidebar-question-order sidebar-question-order-${orderState}`}>
          {String(q.order).padStart(2, '0')}
        </span>
        <span className="sidebar-question-main">
          <span className="sidebar-question-title">{q.title}</span>
        </span>
      </div>
      <QuestionStateLabel q={q} isActive={isActive} />
    </>
  );
}

function QuestionRow({ q, onNavigate, topic }) {
  const stateClass = `sidebar-question-state-${q.state}`;

  if (q.state === 'locked') {
    return (
      <div className={`sidebar-question sidebar-question-locked ${stateClass}`} aria-disabled="true">
        <QuestionContent q={q} />
      </div>
    );
  }

  return (
    <NavLink
      to={`/practice/${topic}/questions/${q.id}`}
      className={({ isActive }) =>
        `sidebar-question ${stateClass} ${isActive ? 'sidebar-question-active' : ''}`
      }
      onClick={onNavigate}
    >
      {({ isActive }) => <QuestionContent q={q} isActive={isActive} />}
    </NavLink>
  );
}

export default function SidebarNav({ catalog, collapsedByDiff, toggleDiff, onNavigate }) {
  const { topic } = useTopic();
  const groups = catalog?.groups ?? [];

  return (
    <div className="sidebar-inner">
      {groups.map((g) => {
        const collapsed = Boolean(collapsedByDiff[g.difficulty]);
        return (
          <div className="sidebar-group" key={g.difficulty}>
            <DifficultyHeader
              difficulty={g.difficulty}
              counts={g.counts}
              collapsed={collapsed}
              onToggle={() => toggleDiff(g.difficulty)}
            />
            {!collapsed && (
              <div className="sidebar-question-list">
                {g.questions
                  .slice()
                  .sort((a, b) => a.order - b.order)
                  .map((q) => (
                    <QuestionRow key={q.id} q={q} onNavigate={onNavigate} topic={topic} />
                  ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
