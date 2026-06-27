import { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, useSearchParams, useParams } from 'react-router-dom';
import Fuse from 'fuse.js';
import { useTopic } from '../contexts/TopicContext';
import { getQuestionFormLabel } from '../questionFormLabel';
import Skeleton from './Skeleton';

// How many concept chips to show before the "show more" toggle
const CHIP_VISIBLE_DEFAULT = 8;

// How many rows to show before "Show all" in an easy group
const EASY_ROW_DEFAULT = 10;

// Mirror of backend/unlock.py thresholds (free plan progressive unlock, code tracks)
const MEDIUM_THRESHOLDS = [8, 15, 25]; // easy_solved → medium unlocks
const HARD_THRESHOLDS   = [8, 15, 22]; // medium_solved → hard unlocks

function computeUnlockNudge(solved, thresholds) {
  const next = thresholds.find(t => t > solved);
  if (!next) return null;
  const prevList = thresholds.filter(t => t <= solved);
  const prev = prevList.length > 0 ? prevList[prevList.length - 1] : 0;
  const gap = next - solved;
  const bracketSize = next - prev;
  const fillPct = Math.round(((bracketSize - gap) / bracketSize) * 100);
  return { gap, fillPct };
}

function titleCase(value) {
  if (!value) return '';
  return `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
}

function conceptSlug(concept) {
  return String(concept || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function DifficultyHeader({ difficulty, counts, collapsed, onToggle, unlockNudge }) {
  const isComplete = counts.solved === counts.total && counts.total > 0;
  return (
    <button
      className={`sidebar-group-header${isComplete ? ' sidebar-group-header-complete' : ''}`}
      onClick={onToggle}
      aria-expanded={!collapsed}
    >
      <div className="sidebar-group-title">
        <span className={`badge badge-${difficulty}`}>{difficulty}</span>
        <div className="sidebar-group-copy">
          <span className="sidebar-group-name">{titleCase(difficulty)}</span>
          <span className="sidebar-group-meta">{counts.solved} solved · {counts.total} total</span>
          {isComplete ? (
            <span className="sidebar-group-complete">✓ Mastered</span>
          ) : unlockNudge ? (
            <div className="sidebar-unlock-bar">
              <div className="sidebar-unlock-bar-track">
                <div className="sidebar-unlock-bar-fill" style={{ width: `${unlockNudge.fillPct}%` }} />
              </div>
              <span className="sidebar-unlock-bar-label">{unlockNudge.gap} more to unlock</span>
            </div>
          ) : null}
        </div>
      </div>
      <div className="sidebar-group-summary">
        <span className={`sidebar-group-count${isComplete ? ' sidebar-group-count-complete' : ''}`}>
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
    return <span className="sidebar-question-label sidebar-question-label-locked" aria-label="Locked">🔒</span>;
  }

  if (q.is_next) {
    return <span className="sidebar-question-label sidebar-question-label-next">Next</span>;
  }

  return null;
}

function QuestionContent({ q, position, isActive = false }) {
  const orderState = isActive ? 'current' : q.state === 'solved' ? 'solved' : q.state === 'locked' ? 'locked' : q.is_next ? 'next' : 'open';
  // Use sequential 1-indexed position within the practice group, not the raw
  // `order` field (which is shared with mock-only questions and can exceed the
  // practice-only count, e.g. showing "51" when there are only 30 questions).
  const displayNum = String(position ?? q.order).padStart(2, '0');

  return (
    <>
      <div className="sidebar-question-leading">
        <span className={`sidebar-question-order sidebar-question-order-${orderState}`}>
          {displayNum}
        </span>
        <span className="sidebar-question-main">
          <span className="sidebar-question-title">{q.title}</span>
        </span>
      </div>
      <QuestionStateLabel q={q} isActive={isActive} />
    </>
  );
}

function QuestionRow({ q, position, onNavigate, topic, pathSlug }) {
  const stateClass = `sidebar-question-state-${q.state}`;
  const lockedClass = q.state === 'locked' ? ' sidebar-question-locked' : '';
  const to = pathSlug
    ? `/practice/${topic}/questions/${q.id}?path=${encodeURIComponent(pathSlug)}`
    : `/practice/${topic}/questions/${q.id}`;

  // Locked questions navigate to preview mode — content visible, Run/Submit disabled.
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `sidebar-question${lockedClass} ${stateClass}${isActive ? ' sidebar-question-active' : ''}`
      }
      onClick={onNavigate}
    >
      {({ isActive }) => <QuestionContent q={q} position={position} isActive={isActive} />}
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

function buildQuestionFormList(groups) {
  const freq = {};
  for (const g of groups) {
    for (const q of g.questions) {
      const formLabel = getQuestionFormLabel(q);
      if (!formLabel) continue;
      freq[formLabel] = (freq[formLabel] ?? 0) + 1;
    }
  }
  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([label]) => label);
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

function QuestionFormFilter({ groups, activeFilters, onToggle, onClear }) {
  const questionForms = useMemo(() => buildQuestionFormList(groups), [groups]);

  if (questionForms.length <= 1) return null;

  const activeList = questionForms.filter((label) => activeFilters.has(label));
  const inactiveList = questionForms.filter((label) => !activeFilters.has(label));

  function renderChip(label) {
    const active = activeFilters.has(label);
    return (
      <button
        key={label}
        className={`sidebar-concept-chip${active ? ' sidebar-concept-chip-active' : ''}`}
        onClick={() => onToggle(label)}
        title={label}
      >
        {label}
        {active && <span className="sidebar-concept-chip-x" aria-hidden="true">×</span>}
      </button>
    );
  }

  return (
    <div className="sidebar-concept-filter sidebar-question-form-filter">
      <div className="sidebar-concept-filter-header">
        <span className="sidebar-concept-filter-label">Filter by question form</span>
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

export default function SidebarNav({ catalog, collapsedByDiff, toggleDiff, onNavigate, plan = 'free', isLoading = false }) {
  const { topic } = useTopic();
  const [searchParams] = useSearchParams();
  const pathSlug = searchParams.get('path');
  const groups = catalog?.groups ?? [];

  // Compute unlock nudges (free plan only)
  const easyGroup = groups.find(g => g.difficulty === 'easy');
  const mediumGroup = groups.find(g => g.difficulty === 'medium');
  const easySolved = easyGroup?.counts?.solved ?? 0;
  const mediumSolved = mediumGroup?.counts?.solved ?? 0;
  const mediumNudge = plan === 'free' ? computeUnlockNudge(easySolved, MEDIUM_THRESHOLDS) : null;
  const hardNudge = plan === 'free' ? computeUnlockNudge(mediumSolved, HARD_THRESHOLDS) : null;

  const [activeFilters, setActiveFilters] = useState(new Set());
  const [activeCompanyFilters, setActiveCompanyFilters] = useState(new Set());
  const [activeQuestionFormFilters, setActiveQuestionFormFilters] = useState(new Set());
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [easyExpanded, setEasyExpanded] = useState(false);
  const [bookmarkedIds, setBookmarkedIds] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');

  const allConcepts = useMemo(() => buildConceptList(groups), [groups]);

  // Map question id → 1-indexed sequential position within its difficulty group.
  // The raw `order` field is shared with mock-only questions and can exceed the
  // practice-only count (e.g. 51 questions shown when there are only 30).
  const positionMap = useMemo(() => {
    const map = new Map();
    for (const g of groups) {
      g.questions.slice().sort((a, b) => a.order - b.order).forEach((q, i) => {
        map.set(q.id, i + 1);
      });
    }
    return map;
  }, [groups]);

  useEffect(() => {
    const raw = searchParams.get('concepts');
    if (!raw) return;

    const requested = raw
      .split(',')
      .map((part) => decodeURIComponent(part).trim().toLowerCase())
      .filter(Boolean);

    if (requested.length === 0 || allConcepts.length === 0) return;

    const conceptBySlug = new Map(
      allConcepts.map((concept) => [conceptSlug(concept), concept])
    );
    const conceptByName = new Map(
      allConcepts.map((concept) => [String(concept).toLowerCase(), concept])
    );

    const selected = new Set();
    requested.forEach((item) => {
      const exact = conceptByName.get(item);
      if (exact) {
        selected.add(exact);
        return;
      }
      const fromSlug = conceptBySlug.get(item);
      if (fromSlug) selected.add(fromSlug);
    });

    if (selected.size > 0) {
      setActiveFilters(selected);
      setFiltersOpen(true);
    }
  }, [allConcepts, searchParams]);

  useEffect(() => {
    const key = `bookmarks:${topic}`;

    const loadBookmarks = () => {
      try {
        const raw = localStorage.getItem(key);
        const parsed = JSON.parse(raw ?? '[]');
        if (Array.isArray(parsed)) {
          setBookmarkedIds(parsed.filter((value) => Number.isInteger(value)).slice(0, 20));
        } else {
          setBookmarkedIds([]);
        }
      } catch {
        setBookmarkedIds([]);
      }
    };

    const handleStorage = (event) => {
      if (!event.key || event.key === key) loadBookmarks();
    };

    const handleBookmarksUpdated = (event) => {
      if (!event?.detail?.topic || event.detail.topic === topic) loadBookmarks();
    };

    loadBookmarks();
    window.addEventListener('storage', handleStorage);
    window.addEventListener('bookmarks-updated', handleBookmarksUpdated);
    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener('bookmarks-updated', handleBookmarksUpdated);
    };
  }, [topic]);

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

  function toggleQuestionFormFilter(label) {
    setActiveQuestionFormFilters((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  function clearQuestionFormFilters() {
    setActiveQuestionFormFilters(new Set());
  }

  function clearAllFilters() {
    clearFilters();
    clearCompanyFilters();
    clearQuestionFormFilters();
    setSearchQuery('');
  }

  const anyFilterActive = activeFilters.size > 0 || activeCompanyFilters.size > 0 || activeQuestionFormFilters.size > 0;
  const totalActiveFilters = activeFilters.size + activeCompanyFilters.size + activeQuestionFormFilters.size;

  const searchMatchesById = useMemo(() => {
    const query = searchQuery.trim();
    if (!query) return null;
    const normalizedQuery = query.toLowerCase();

    const entries = [];
    groups.forEach((group) => {
      group.questions.forEach((question) => {
        entries.push({
          id: Number(question.id),
          title: question.title ?? '',
          concepts: question.concepts ?? [],
          difficulty: group.difficulty ?? '',
          questionForm: getQuestionFormLabel(question) ?? '',
        });
      });
    });

    if (entries.length === 0) return new Set();

    const directMatches = entries
      .filter((entry) => {
        const title = String(entry.title || '').toLowerCase();
        const difficulty = String(entry.difficulty || '').toLowerCase();
        const concepts = (entry.concepts || []).join(' ').toLowerCase();
        const questionForm = String(entry.questionForm || '').toLowerCase();
        return title.includes(normalizedQuery)
          || difficulty.includes(normalizedQuery)
          || concepts.includes(normalizedQuery)
          || questionForm.includes(normalizedQuery);
      })
      .map((entry) => Number(entry.id));

    if (directMatches.length > 0) {
      return new Set(directMatches);
    }

    const fuse = new Fuse(entries, {
      includeScore: true,
      threshold: 0.35,
      ignoreLocation: true,
      keys: [
        { name: 'title', weight: 0.7 },
        { name: 'concepts', weight: 0.2 },
        { name: 'questionForm', weight: 0.15 },
        { name: 'difficulty', weight: 0.05 },
      ],
    });

    return new Set(
      fuse
        .search(query, { limit: 60 })
        .filter((result) => (result.score ?? 1) <= 0.28)
        .map((result) => Number(result.item.id))
    );
  }, [groups, searchQuery]);

  // Apply concept + company + question form filters (AND logic)
  const filteredGroups = useMemo(() => {
    if (!anyFilterActive && !searchMatchesById) return groups;
    return groups.map((g) => {
      const questions = g.questions.filter((q) => {
        const conceptMatch = activeFilters.size === 0 || (q.concepts ?? []).some((c) => activeFilters.has(c));
        const companyMatch = activeCompanyFilters.size === 0 || (q.companies ?? []).some((c) => activeCompanyFilters.has(c));
        const questionFormLabel = getQuestionFormLabel(q);
        const questionFormMatch = activeQuestionFormFilters.size === 0 || (questionFormLabel && activeQuestionFormFilters.has(questionFormLabel));
        const textMatch = !searchMatchesById || searchMatchesById.has(Number(q.id));
        return conceptMatch && companyMatch && questionFormMatch && textMatch;
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
  }, [groups, activeFilters, activeCompanyFilters, activeQuestionFormFilters, anyFilterActive, searchMatchesById]);

  const bookmarkedQuestions = useMemo(() => {
    if (!bookmarkedIds.length) return [];
    const byId = new Map();
    groups.forEach((group) => {
      group.questions.forEach((question) => byId.set(Number(question.id), question));
    });
    return bookmarkedIds
      .map((id) => byId.get(Number(id)))
      .filter(Boolean);
  }, [bookmarkedIds, groups]);

  // --- Active-question reveal (the fix for "sidebar stuck on the default view") ---
  const { id: activeIdParam } = useParams();
  const activeId = activeIdParam != null ? Number(activeIdParam) : null;
  const sidebarRef = useRef(null);

  // If the active question is an easy question beyond the collapsed row cap, expand
  // the easy list so its row is actually rendered (otherwise it hides behind "Show all").
  useEffect(() => {
    if (activeId == null) return;
    const easyG = groups.find((g) => g.difficulty === 'easy');
    if (!easyG) return;
    const sortedEasy = easyG.questions.slice().sort((a, b) => a.order - b.order);
    const idx = sortedEasy.findIndex((q) => Number(q.id) === activeId);
    if (idx >= EASY_ROW_DEFAULT) setEasyExpanded(true);
  }, [activeId, groups]);

  // Scroll the active row into view once its group / the easy list has expanded.
  // block:'nearest' is a no-op when it's already visible. Re-runs when the active id
  // or any visibility-affecting state changes, so it fires after the group opens.
  useEffect(() => {
    if (activeId == null) return;
    const el = sidebarRef.current?.querySelector('.sidebar-question-active');
    if (el) el.scrollIntoView({ block: 'nearest' });
  }, [activeId, collapsedByDiff, easyExpanded, filteredGroups]);

  if (isLoading) {
    return (
      <div className="sidebar-inner sidebar-inner-loading" aria-label="Loading question bank">
        <div className="sidebar-search-block">
          <Skeleton className="sidebar-skeleton-search" height="2rem" />
        </div>
        {[0, 1, 2].map((groupIndex) => (
          <div className="sidebar-group" key={`loading-${groupIndex}`}>
            <Skeleton className="sidebar-skeleton-group-head" height="3.1rem" />
            <div className="sidebar-question-list sidebar-skeleton-list">
              {[0, 1, 2, 3].map((rowIndex) => (
                <Skeleton key={`loading-${groupIndex}-${rowIndex}`} className="sidebar-skeleton-row" height="2.2rem" />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="sidebar-inner" ref={sidebarRef}>
      <div className="sidebar-search-block">
        <label className="sidebar-search-label" htmlFor="sidebar-question-search">Search questions</label>
        <div className="sidebar-search-input-wrap">
          <input
            id="sidebar-question-search"
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Title, concept, form, or difficulty"
            className="sidebar-search-input"
          />
          {searchQuery.trim() && (
            <button
              className="sidebar-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear question search"
              title="Clear search"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="sidebar-filters-accordion">
        <div className={`sidebar-filters-toggle${anyFilterActive ? ' sidebar-filters-toggle-active' : ''}`}>
          <button
            type="button"
            className="sidebar-filters-toggle-main"
            onClick={() => setFiltersOpen(v => !v)}
            aria-expanded={filtersOpen}
          >
            <span className="sidebar-filters-toggle-label">
              Filters
              {totalActiveFilters > 0 && (
                <span className="sidebar-filters-badge">{totalActiveFilters}</span>
              )}
            </span>
            <span className="sidebar-filters-toggle-right">
              <span className="sidebar-chevron">{filtersOpen ? '▾' : '▸'}</span>
            </span>
          </button>
          {anyFilterActive && !filtersOpen && (
            <button
              type="button"
              className="sidebar-concept-clear sidebar-filters-clear-inline"
              onClick={clearAllFilters}
              title="Clear all filters"
              aria-label="Clear all filters"
            >
              Clear
            </button>
          )}
        </div>

        {filtersOpen && (
          <div className="sidebar-filters-body">
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
            <QuestionFormFilter
              groups={groups}
              activeFilters={activeQuestionFormFilters}
              onToggle={toggleQuestionFormFilter}
              onClear={clearQuestionFormFilters}
            />
          </div>
        )}
      </div>

      {(anyFilterActive || searchMatchesById) && filteredGroups.length === 0 && (
        <div className="sidebar-concept-empty">
          No questions match.{' '}
          <button className="sidebar-concept-clear" onClick={clearAllFilters}>
            Clear all
          </button>
        </div>
      )}

      {bookmarkedQuestions.length > 0 && (
        <div className="sidebar-group sidebar-group-bookmarks">
          <div className="sidebar-group-header sidebar-group-header-static">
            <div className="sidebar-group-title">
              <span className="badge badge-medium">saved</span>
              <div className="sidebar-group-copy">
                <span className="sidebar-group-name">Bookmarked</span>
                <span className="sidebar-group-meta">{bookmarkedQuestions.length} saved</span>
              </div>
            </div>
          </div>
          <div className="sidebar-question-list">
            {bookmarkedQuestions.map((q) => (
              <QuestionRow key={`bookmark-${q.id}`} q={q} position={positionMap.get(q.id)} onNavigate={onNavigate} topic={topic} pathSlug={pathSlug} />
            ))}
          </div>
        </div>
      )}

      {filteredGroups.map((g) => {
        const collapsed = Boolean(collapsedByDiff[g.difficulty]);
        const hasLockedQuestions = g.questions.some(q => q.state === 'locked');
        const nudge = g.difficulty === 'medium' && hasLockedQuestions ? mediumNudge
          : g.difficulty === 'hard' && hasLockedQuestions ? hardNudge
          : null;
        const sorted = g.questions.slice().sort((a, b) => a.order - b.order);
        const isEasy = g.difficulty === 'easy';
        const showRowCap = isEasy && !easyExpanded && sorted.length > EASY_ROW_DEFAULT;
        const visibleQuestions = showRowCap ? sorted.slice(0, EASY_ROW_DEFAULT) : sorted;
        const hiddenEasyCount = sorted.length - EASY_ROW_DEFAULT;

        return (
          <div className="sidebar-group" key={g.difficulty}>
            <DifficultyHeader
              difficulty={g.difficulty}
              counts={g.counts}
              collapsed={collapsed}
              onToggle={() => toggleDiff(g.difficulty)}
              unlockNudge={nudge}
            />
            {!collapsed && (
              <div className="sidebar-question-list">
                {visibleQuestions.map((q) => (
                  <QuestionRow key={q.id} q={q} position={positionMap.get(q.id)} onNavigate={onNavigate} topic={topic} pathSlug={pathSlug} />
                ))}
                {showRowCap && (
                  <button
                    className="sidebar-show-all-btn"
                    onClick={() => setEasyExpanded(true)}
                  >
                    Show all {sorted.length} easy →
                  </button>
                )}
                {isEasy && easyExpanded && hiddenEasyCount > 0 && (
                  <button
                    className="sidebar-show-all-btn sidebar-show-all-btn-less"
                    onClick={() => setEasyExpanded(false)}
                  >
                    Show less ▴
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
