import { NavLink } from 'react-router-dom';

function DifficultyHeader({ difficulty, counts, collapsed, onToggle }) {
  return (
    <button className="sidebar-group-header" onClick={onToggle}>
      <div className="sidebar-group-title">
        <span className={`badge badge-${difficulty}`}>{difficulty}</span>
        <span className="sidebar-group-count">
          {counts.solved}/{counts.total}
        </span>
      </div>
      <span className="sidebar-chevron">{collapsed ? '▸' : '▾'}</span>
    </button>
  );
}

function QuestionRow({ q, onNavigate }) {
  const content = (
    <>
      <span className={`status-dot status-${q.state}`} aria-hidden="true" />
      <span className="sidebar-question-title">{q.order}. {q.title}</span>
      {q.is_next && q.state !== 'solved' && <span className="sidebar-next">Next</span>}
      {q.state === 'solved' && <span className="sidebar-solved">Solved</span>}
      {q.state === 'locked' && <span className="sidebar-locked">Locked</span>}
    </>
  );

  if (q.state === 'locked') {
    return (
      <div className="sidebar-question sidebar-question-locked" aria-disabled="true">
        {content}
      </div>
    );
  }

  return (
    <NavLink
      to={`/practice/questions/${q.id}`}
      className={({ isActive }) =>
        `sidebar-question ${isActive ? 'sidebar-question-active' : ''}`
      }
      onClick={onNavigate}
    >
      {content}
    </NavLink>
  );
}

export default function SidebarNav({ catalog, collapsedByDiff, toggleDiff, onNavigate }) {
  const groups = catalog?.groups ?? [];

  return (
    <div className="sidebar-inner">
      <div className="sidebar-header">
        <div className="sidebar-title">Question Bank</div>
        <div className="sidebar-subtitle">Progress is per-browser session.</div>
      </div>

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
                    <QuestionRow key={q.id} q={q} onNavigate={onNavigate} />
                  ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
