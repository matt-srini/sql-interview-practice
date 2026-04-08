import { useMemo, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useTopic } from '../contexts/TopicContext';

// How many concept chips to show before the "show more" toggle
const CHIP_VISIBLE_DEFAULT = 8;

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

// Build sorted concept list: most-frequent concepts first
function buildConceptList(groups) {
  const freq = {};
  for (const g of groups) {
    for (const q of g.questions) {
      for (const c of q.concepts ?? []) {
        freq[c] = (freq[c] ?? 0) + 1;
      }
    }
  }
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([concept]) => concept);
}

// Build sorted company list: most-frequent companies first
function buildCompanyList(groups) {
  const freq = {};
  for (const g of groups) {
    for (const q of g.questions) {
      for (const c of q.companies ?? []) {
        freq[c] = (freq[c] ?? 0) + 1;
      }
    }
  }
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([company]) => company);
}

function ConceptFilter({ groups, activeFilters, onToggle, onClear }) {
  const [expanded, setExpanded] = useState(false);
  const filterRef = useRef(null);
  const concepts = useMemo(() => buildConceptList(groups), [groups]);

  if (concepts.length === 0) return null;

  // Active chips always float to the top and are always visible.
  // Inactive chips fill remaining slots up to CHIP_VISIBLE_DEFAULT when collapsed.
  const activeList   = concepts.filter((c) => activeFilters.has(c));
  const inactiveList = concepts.filter((c) => !activeFilters.has(c));
  const inactiveSlots = Math.max(0, CHIP_VISIBLE_DEFAULT - activeList.length);
  const visibleInactive = expanded ? inactiveList : inactiveList.slice(0, inactiveSlots);
  const hiddenCount = inactiveList.length - inactiveSlots;

  function renderChip(concept) {
    const active = activeFilters.has(concept);
    return (
      <button
        key={concept}
        className={`sidebar-concept-chip${active ? ' sidebar-concept-chip-active' : ''}`}
        onClick={() => onToggle(concept)}
        title={concept}
      >
        {concept}
        {active && <span className="sidebar-concept-chip-x" aria-hidden="true">×</span>}
      </button>
    );
  }

  function collapse() {
    setExpanded(false);
    filterRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }

  return (
    <div className="sidebar-concept-filter" ref={filterRef}>
      <div className="sidebar-concept-filter-header">
        <span className="sidebar-concept-filter-label">Filter by concept</span>
        {activeFilters.size > 0 && (
          <button className="sidebar-concept-clear" onClick={onClear}>
            Clear
          </button>
        )}
      </div>
      <div className="sidebar-concept-chips">
        {activeList.map(renderChip)}
        {visibleInactive.map(renderChip)}
        {!expanded && hiddenCount > 0 && (
          <button
            className="sidebar-concept-chip sidebar-concept-chip-more"
            onClick={() => setExpanded(true)}
          >
            +{hiddenCount} more ▾
          </button>
        )}
        {expanded && hiddenCount > 0 && (
          <button
            className="sidebar-concept-chip sidebar-concept-chip-more"
            onClick={collapse}
          >
            show less ▴
          </button>
        )}
      </div>
    </div>
  );
}

function CompanyFilter({ groups, activeFilters, onToggle, onClear }) {
  const companies = useMemo(() => buildCompanyList(groups), [groups]);

  if (companies.length === 0) return null;

  const activeList = companies.filter((c) => activeFilters.has(c));
  const inactiveList = companies.filter((c) => !activeFilters.has(c));

  function renderChip(company) {
    const active = activeFilters.has(company);
    return (
      <button
        key={company}
        className={`sidebar-concept-chip${active ? ' sidebar-concept-chip-active' : ''}`}
        onClick={() => onToggle(company)}
        title={company}
      >
        {company}
        {active && <span className="sidebar-concept-chip-x" aria-hidden="true">×</span>}
      </button>
    );
  }

  return (
    <div className="sidebar-concept-filter sidebar-company-filter">
      <div className="sidebar-concept-filter-header">
        <span className="sidebar-concept-filter-label">Filter by company</span>
        {activeFilters.size > 0 && (
          <button className="sidebar-concept-clear" onClick={onClear}>
            Clear
          </button>
        )}
      </div>
      <div className="sidebar-concept-chips">
        {activeList.map(renderChip)}
        {inactiveList.map(renderChip)}
      </div>
    </div>
  );
}

export default function SidebarNav({ catalog, collapsedByDiff, toggleDiff, onNavigate }) {
  const { topic } = useTopic();
  const groups = catalog?.groups ?? [];

  const [activeFilters, setActiveFilters] = useState(new Set());
  const [activeCompanyFilters, setActiveCompanyFilters] = useState(new Set());

  function toggleFilter(concept) {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(concept)) next.delete(concept);
      else next.add(concept);
      return next;
    });
  }

  function clearFilters() {
    setActiveFilters(new Set());
  }

  function toggleCompanyFilter(company) {
    setActiveCompanyFilters((prev) => {
      const next = new Set(prev);
      if (next.has(company)) next.delete(company);
      else next.add(company);
      return next;
    });
  }

  function clearCompanyFilters() {
    setActiveCompanyFilters(new Set());
  }

  const anyFilterActive = activeFilters.size > 0 || activeCompanyFilters.size > 0;

  // Apply concept + company filters (AND logic: question must satisfy both)
  const filteredGroups = useMemo(() => {
    if (!anyFilterActive) return groups;
    return groups.map((g) => {
      const questions = g.questions.filter((q) => {
        const conceptMatch = activeFilters.size === 0 || (q.concepts ?? []).some((c) => activeFilters.has(c));
        const companyMatch = activeCompanyFilters.size === 0 || (q.companies ?? []).some((c) => activeCompanyFilters.has(c));
        return conceptMatch && companyMatch;
      });
      return {
        ...g,
        questions,
        counts: {
          ...g.counts,
          total: questions.length,
          solved: questions.filter((q) => q.state === 'solved').length,
        },
      };
    }).filter((g) => g.questions.length > 0);
  }, [groups, activeFilters, activeCompanyFilters, anyFilterActive]);

  return (
    <div className="sidebar-inner">
      <ConceptFilter
        groups={groups}
        activeFilters={activeFilters}
        onToggle={toggleFilter}
        onClear={clearFilters}
      />
      <CompanyFilter
        groups={groups}
        activeFilters={activeCompanyFilters}
        onToggle={toggleCompanyFilter}
        onClear={clearCompanyFilters}
      />

      {anyFilterActive && filteredGroups.length === 0 && (
        <div className="sidebar-concept-empty">
          No questions match these filters.{' '}
          <button className="sidebar-concept-clear" onClick={() => { clearFilters(); clearCompanyFilters(); }}>
            Clear filters
          </button>
        </div>
      )}

      {filteredGroups.map((g) => {
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
