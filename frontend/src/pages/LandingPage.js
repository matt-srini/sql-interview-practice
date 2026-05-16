import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { ALL_TRACK_SLUGS, TRACK_SLUGS } from '../trackRegistry';
import PathProgressCard from '../components/PathProgressCard';
import Topbar from '../components/Topbar';
import UpgradeButton from '../components/UpgradeButton';
import { detectCurrency, PRICES } from '../utils/currency';

// ── Role → track weighting ──────────────────────────────────────────────────
const ROLES = [
  {
    id: 'analyst',
    label: 'Data Analyst',
    tagline: 'SQL depth · statistical reasoning · Python for data',
    tracks: ['sql', 'statistics', 'python-data', 'python'],
  },
  {
    id: 'engineer',
    label: 'Data Engineer',
    tagline: 'Python pipelines · distributed systems · DE concepts',
    tracks: ['python', 'sql', 'pyspark', 'data-engineering', 'data-modeling'],
  },
  {
    id: 'analytics_engineer',
    label: 'Analytics Engineer',
    tagline: 'SQL precision · data modeling · dbt patterns',
    tracks: ['sql', 'data-modeling', 'python-data', 'python'],
  },
  {
    id: 'scientist',
    label: 'Data Scientist',
    tagline: 'Python · statistical inference · SQL for analysis',
    tracks: ['python', 'statistics', 'sql', 'python-data'],
  },
];

// ── Hero IDE content ────────────────────────────────────────────────────────
const IDE_QUERY = `WITH ranked AS (
  SELECT
    name, dept, salary,
    RANK() OVER (
      PARTITION BY dept
      ORDER BY salary DESC
    ) AS rnk
  FROM employees
)
SELECT name, dept, salary
FROM ranked
WHERE rnk = 1;`;

const IDE_COLS = ['name', 'dept', 'salary'];
const IDE_ROWS = [
  ['Sarah K.',  'Engineering', '$145,200'],
  ['Jordan T.', 'Product',     '$131,800'],
  ['Priya N.',  'Analytics',   '$119,500'],
  ['Alex M.',   'Design',      '$108,300'],
];

// ── Shared hooks ────────────────────────────────────────────────────────────
function useInView(ref, margin = '-8%') {
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setInView(true); },
      { rootMargin: margin, threshold: 0.05 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return inView;
}

function useCountUp(target, duration, trigger) {
  const [val, setVal] = useState(0);
  const ran = useRef(false);
  useEffect(() => {
    if (!trigger || ran.current) return;
    ran.current = true;
    const start = performance.now();
    function tick(now) {
      const p = Math.min((now - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(ease * target));
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }, [trigger, target, duration]);
  return val;
}

// ── Hero IDE typing animation ────────────────────────────────────────────────
function HeroIDE({ reduced }) {
  const TOTAL = IDE_QUERY.length;
  const [typedLen, setTypedLen] = useState(reduced ? TOTAL : 0);
  const [phase, setPhase] = useState(reduced ? 'done' : 'typing');
  const [visibleRows, setVisibleRows] = useState(reduced ? IDE_ROWS.length : 0);
  const [flashIdx, setFlashIdx] = useState(null);

  useEffect(() => {
    if (phase !== 'typing') return;
    if (typedLen >= TOTAL) { setTimeout(() => setPhase('running'), 350); return; }
    const t = setTimeout(() => setTypedLen(n => n + 1), 26);
    return () => clearTimeout(t);
  }, [phase, typedLen, TOTAL]);

  useEffect(() => {
    if (phase !== 'running') return;
    const t = setTimeout(() => setPhase('streaming'), 550);
    return () => clearTimeout(t);
  }, [phase]);

  useEffect(() => {
    if (phase !== 'streaming') return;
    if (visibleRows >= IDE_ROWS.length) { setPhase('done'); return; }
    const t = setTimeout(() => {
      const idx = visibleRows;
      setVisibleRows(n => n + 1);
      setFlashIdx(idx);
      setTimeout(() => setFlashIdx(null), 180);
    }, 55);
    return () => clearTimeout(t);
  }, [phase, visibleRows]);

  const showResult = phase === 'streaming' || phase === 'done';
  const showRunning = phase === 'running';

  return (
    <div className="lp-ide" aria-label="Live query execution preview" aria-hidden="true">
      <div className="lp-ide-chrome">
        <span className="lp-ide-dots"><i /><i /><i /></span>
        <span className="lp-ide-fname">dept_ranking.sql</span>
        <span className="lp-ide-badge">SQL · DuckDB</span>
      </div>
      <div className="lp-ide-body">
        {/* Full query always in DOM — untyped chars are transparent so height is stable */}
        <pre className="lp-ide-query"><code>
          {Array.from(IDE_QUERY).map((ch, i) => (
            <span key={i} style={i >= typedLen ? { color: 'transparent' } : undefined}>{ch}</span>
          ))}
          {phase !== 'done' && <span className="lp-ide-cursor" />}
        </code></pre>
        {/* Result always in DOM — unshown rows use visibility:hidden to preserve height */}
        <div className="lp-ide-result">
          {showRunning && <p className="lp-ide-running" style={{ position: 'absolute', marginTop: '-4px' }}>Running…</p>}
          <table>
            <thead>
              <tr>{IDE_COLS.map(c => <th key={c}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {IDE_ROWS.map((row, i) => (
                <tr
                  key={i}
                  className={flashIdx === i ? 'lp-ide-row--flash' : ''}
                  style={{ visibility: i < visibleRows ? 'visible' : 'hidden' }}
                >
                  {row.map((cell, j) => <td key={j}>{cell}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="lp-ide-rowcount" style={{ visibility: phase === 'done' ? 'visible' : 'hidden' }}>
            {IDE_ROWS.length} rows · 0 errors
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Section entrance animation wrapper ─────────────────────────────────────
function Reveal({ children, delay = 0, className = '' }) {
  const ref = useRef(null);
  const inView = useInView(ref);
  return (
    <div
      ref={ref}
      className={`lp-reveal${inView ? ' is-visible' : ''} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}

// ── Section 01: Hero ────────────────────────────────────────────────────────
function HeroSection({ user, dashData, reduced }) {
  if (user) {
    const recent = dashData?.recent_activity?.[0];
    const topic = recent?.topic || 'sql';
    const meta = TRACK_META[topic] || TRACK_META.sql;
    const href = recent
      ? `/practice/${topic}/questions/${recent.question_id}`
      : `/practice/${topic}`;
    const firstName = (user?.name || user?.email || '').split(/[\s@]/)[0] || 'there';
    const totalSolved = dashData
      ? Object.values(dashData.tracks || {}).reduce((s, t) => s + (t?.solved ?? 0), 0)
      : 0;

    return (
      <section className="lp-section lp-hero-loggedin">
        <div className="lp-inner">
          <p className="lp-eyebrow">Welcome back, {firstName}</p>
          <p className="lp-hero-li-copy">
            {totalSolved > 0
              ? `${totalSolved} solved so far — keep the streak going.`
              : 'Ready when you are.'}
          </p>
          <div className="lp-hero-li-cards">
            <Link to={href} className="lp-li-card lp-li-card--primary" style={{ '--card-color': meta.color }}>
              <span className="lp-li-card-eye">Resume</span>
              <span className="lp-li-card-title">{meta.label} track</span>
              <span className="lp-li-card-cta">Open →</span>
            </Link>
            <Link to="/dashboard" className="lp-li-card">
              <span className="lp-li-card-eye">Progress</span>
              <span className="lp-li-card-title">Dashboard</span>
              <span className="lp-li-card-cta">View →</span>
            </Link>
            <Link to="/mock" className="lp-li-card">
              <span className="lp-li-card-eye">Interview</span>
              <span className="lp-li-card-title">Mock session</span>
              <span className="lp-li-card-cta">Start →</span>
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="lp-section lp-hero">
      <div className="lp-inner lp-hero-inner">
        <div className="lp-hero-left">
          <p className="lp-eyebrow">Interview preparation, reasoned</p>
          <h1 className="lp-hero-h1">
            Build the reasoning skills data interviews actually test.
          </h1>
          <p className="lp-hero-sub">
            Real datasets. Real execution. The kind of thinking that earns the offer.
          </p>
          <div className="lp-hero-actions">
            <Link className="btn btn-primary" to="/auth">Start thinking →</Link>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                const el = document.getElementById('lp-roles');
                if (!el) return;
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
            >
              Find your track ↓
            </button>
          </div>
        </div>
        <div className="lp-hero-right">
          <HeroIDE reduced={reduced} />
        </div>
      </div>
    </section>
  );
}

// ── Section 02: The Thesis ──────────────────────────────────────────────────
function ThesisSection() {
  const COLS = [
    {
      index: '01',
      title: 'Recognition ≠ reasoning',
      copy: 'Knowing that window functions exist is not the same as knowing when to use them. This platform trains the second skill — the one that shows up under pressure.',
    },
    {
      index: '02',
      title: 'Execution, not explanation',
      copy: 'Your SQL hits a real DuckDB engine. Your Python runs in an isolated sandbox. You see actual output — rows, errors, mismatch details — not a simulated pass/fail.',
    },
    {
      index: '03',
      title: 'Answers are earned',
      copy: 'Progressive hints surface the mental model first, the technique second. Solutions only appear after you\'ve exhausted hints. You reason your way to understanding.',
    },
  ];

  return (
    <section className="lp-section lp-thesis lp-section-rule">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">02&ensp;/&ensp;THE THESIS</p>
          <h2 className="lp-section-h2">What data thinking is.</h2>
        </Reveal>
        <div className="lp-thesis-cols">
          {COLS.map((col, i) => (
            <Reveal key={col.index} delay={i * 80}>
              <div className="lp-thesis-col">
                <span className="lp-thesis-col-index">{col.index}</span>
                <h3 className="lp-thesis-col-title">{col.title}</h3>
                <p className="lp-thesis-col-copy">{col.copy}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Section 03: Wrong way / Right way ──────────────────────────────────────
function WrongRightSection() {
  const ROWS = [
    { wrong: 'Flash cards → recognition',    right: 'Reason → Write' },
    { wrong: 'AI answers → you read',         right: 'Run' },
    { wrong: 'Syntax drills → no reasoning',  right: 'Compare' },
    { wrong: 'One-shot practice → no pattern', right: 'Understand' },
  ];

  const ref = useRef(null);
  const inView = useInView(ref, '-10%');

  return (
    <section className="lp-section lp-wrongright lp-section-rule">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">03&ensp;/&ensp;THE APPROACH</p>
          <h2 className="lp-section-h2">The wrong way. The right way.</h2>
        </Reveal>
        <div className="lp-wr-table" ref={ref}>
          <div className="lp-wr-col lp-wr-col--wrong">
            <p className="lp-wr-col-head">Others</p>
            {ROWS.map((r, i) => (
              <p key={i} className="lp-wr-row lp-wr-row--wrong">{r.wrong}</p>
            ))}
          </div>
          <div className="lp-wr-divider" aria-hidden="true" />
          <div className="lp-wr-col lp-wr-col--right">
            <p className="lp-wr-col-head">datathink</p>
            {ROWS.map((r, i) => (
              <p
                key={i}
                className={`lp-wr-row lp-wr-row--right${inView ? ' is-visible' : ''}`}
                style={{ transitionDelay: inView ? `${i * 90}ms` : '0ms' }}
              >
                {r.right}
              </p>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Section 04: Role selector ───────────────────────────────────────────────
function RoleSelectorSection({ dashData }) {
  const [activeRole, setActiveRole] = useState(0);
  const role = ROLES[activeRole];

  return (
    <section className="lp-section lp-roles lp-section-rule" id="lp-roles">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">04&ensp;/&ensp;YOUR ROLE</p>
          <h2 className="lp-section-h2">Your role shapes which thinking matters.</h2>
          <p className="lp-section-sub">
            Seven tracks — here by relevance, not as a grid.
          </p>
        </Reveal>

        <div
          className="lp-role-tabs"
          role="tablist"
          aria-label="Select your data role"
        >
          {ROLES.map((r, i) => (
            <button
              key={r.id}
              role="tab"
              aria-selected={activeRole === i}
              aria-controls={`lp-role-panel-${r.id}`}
              id={`lp-role-tab-${r.id}`}
              className={`lp-role-tab${activeRole === i ? ' is-active' : ''}`}
              onClick={() => setActiveRole(i)}
              onKeyDown={(e) => {
                if (e.key === 'ArrowRight') setActiveRole((activeRole + 1) % ROLES.length);
                if (e.key === 'ArrowLeft') setActiveRole((activeRole + ROLES.length - 1) % ROLES.length);
              }}
            >
              {r.label}
            </button>
          ))}
        </div>

        <div
          id={`lp-role-panel-${role.id}`}
          role="tabpanel"
          aria-labelledby={`lp-role-tab-${role.id}`}
          className="lp-role-panel"
        >
          <p className="lp-role-tagline">{role.tagline}</p>
          <div className="lp-role-tracks">
            {role.tracks.map((slug, i) => {
              const meta = TRACK_META[slug];
              if (!meta) return null;
              const isActive = TRACK_SLUGS.includes(slug);
              const trackData = dashData?.tracks?.[slug];
              const solved = trackData?.solved ?? 0;
              return (
                <Reveal key={slug} delay={i * 60} className="lp-role-track-reveal">
                  <div className="lp-role-track" style={{ '--track-color': meta.color }}>
                    <div className="lp-role-track-header">
                      <span className="lp-role-track-dot" aria-hidden="true" />
                      <span className="lp-role-track-name">{meta.label}</span>
                      {meta.comingSoon && (
                        <span className="lp-badge-soon">Coming soon</span>
                      )}
                      {!meta.comingSoon && solved > 0 && (
                        <span className="lp-role-track-progress">{solved} solved</span>
                      )}
                    </div>
                    <p className="lp-role-track-desc">{meta.description}</p>
                    <div className="lp-role-track-footer">
                      <span className="lp-role-track-tagline">{meta.tagline}</span>
                      {isActive ? (
                        <Link
                          to={`/practice/${slug}`}
                          className="lp-role-track-cta"
                          style={{ color: meta.color }}
                        >
                          {solved > 0 ? 'Continue →' : 'Open track →'}
                        </Link>
                      ) : (
                        <span className="lp-role-track-cta lp-role-track-cta--soon">
                          In development
                        </span>
                      )}
                    </div>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

// ── Section 05: Proof strip ─────────────────────────────────────────────────
const TOTAL_QUESTIONS = ALL_TRACK_SLUGS.reduce(
  (s, slug) => s + (TRACK_META[slug]?.totalQuestions ?? 0), 0
);

function ProofStripSection() {
  const ref = useRef(null);
  const inView = useInView(ref, '-5%');
  const reduced = typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const qCount = useCountUp(TOTAL_QUESTIONS, 700, reduced || inView);
  const trackCount = useCountUp(ALL_TRACK_SLUGS.length, 500, reduced || inView);

  const STATS = [
    { num: trackCount, label: 'tracks' },
    { num: `${qCount}+`, label: 'engineered questions' },
    { text: 'real DuckDB execution' },
    { text: 'live Python sandbox' },
    { text: 'mocks withhold solutions' },
  ];

  return (
    <section className="lp-section lp-proof lp-section-rule" ref={ref}>
      <div className="lp-inner">
        <div className="lp-proof-strip">
          {STATS.map((s, i) => (
            <span key={i} className="lp-proof-stat">
              {s.num !== undefined
                ? <><strong>{s.num}</strong> {s.label}</>
                : s.text
              }
            </span>
          ))}
        </div>
        <p className="lp-proof-sub">
          Questions modeled on interviews at Meta, Stripe, Airbnb, Google, Amazon, and Uber.
        </p>
      </div>
    </section>
  );
}

// ── Section 06: Tracks index ────────────────────────────────────────────────
function TracksIndexSection() {
  const FORMAT_LABELS = {
    sql:                'SQL · DuckDB',
    python:             'Python · sandbox',
    'python-data':      'Pandas · sandbox',
    pyspark:            'MCQ · predict output',
    'data-engineering': 'MCQ · scenario',
    'data-modeling':    'MCQ · schema design',
    statistics:         'MCQ + numerical',
  };

  return (
    <section className="lp-section lp-tracks lp-section-rule" id="lp-tracks">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">06&ensp;/&ensp;ALL TRACKS</p>
          <h2 className="lp-section-h2">The full curriculum.</h2>
        </Reveal>
        <div className="lp-tracks-list" role="list">
          {ALL_TRACK_SLUGS.map((slug, i) => {
            const meta = TRACK_META[slug];
            const isActive = TRACK_SLUGS.includes(slug);
            const totalQ = meta.totalQuestions;
            return (
              <Reveal key={slug} delay={i * 40}>
                <div role="listitem" className={`lp-track-row${meta.comingSoon ? ' lp-track-row--soon' : ''}`}>
                  <span className="lp-track-dot" style={{ background: meta.color }} aria-hidden="true" />
                  <div className="lp-track-info">
                    <div className="lp-track-name-row">
                      <span className="lp-track-name">{meta.label}</span>
                      {meta.comingSoon && <span className="lp-badge-soon">Coming soon</span>}
                    </div>
                    <p className="lp-track-desc">{meta.description}</p>
                  </div>
                  <div className="lp-track-meta">
                    <span className="lp-track-count">{totalQ} q</span>
                    <span className="lp-track-format">{FORMAT_LABELS[slug] ?? meta.tagline}</span>
                  </div>
                  {isActive ? (
                    <Link
                      to={`/practice/${slug}`}
                      className="lp-track-enter"
                      style={{ '--row-color': meta.color }}
                      aria-label={`Open ${meta.label} track`}
                    >
                      Enter →
                    </Link>
                  ) : (
                    <span className="lp-track-enter lp-track-enter--soon">Soon</span>
                  )}
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ── Section 07: Pricing ─────────────────────────────────────────────────────
function PricingSection({ userPlan, currency }) {
  const p = PRICES[currency];

  function proColCta() {
    if (userPlan === 'lifetime_pro')  return 'current';
    if (userPlan === 'pro')           return 'lifetime_only';
    if (userPlan === 'free')          return 'both';
    return 'none';
  }
  function eliteColCta() {
    if (userPlan === 'lifetime_elite') return 'current';
    if (userPlan === 'elite')          return 'lifetime_only';
    return 'both';
  }

  const ACTIVE_Q = TRACK_SLUGS.reduce((s, slug) => s + (TRACK_META[slug]?.totalQuestions ?? 0), 0);
  const FREE_EASY = TRACK_SLUGS
    .filter(s => !TRACK_META[s]?.comingSoon)
    .map(s => {
      const m = TRACK_META[s];
      const easy = { sql: 32, python: 30, 'python-data': 22, pyspark: 38, 'data-engineering': 30 }[s] ?? 0;
      return `${easy} ${m.label}`;
    })
    .join(' · ');

  return (
    <section className="lp-section lp-section-rule" id="landing-pricing">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">07&ensp;/&ensp;PRICING</p>
          <h2 className="lp-section-h2">Straightforward pricing.</h2>
        </Reveal>
        <div className="landing-tier-grid">

          <div className="landing-tier-col">
            <div className="landing-tier-col-header">
              <span className="landing-tier-name">Free</span>
              <div className="landing-tier-price">
                <span className="landing-tier-price-amount">Free</span>
              </div>
            </div>
            <ul className="landing-tier-list">
              <li>All easy questions ({FREE_EASY})</li>
              <li>Medium + hard unlock as you solve (hard cap: 8 per code track, 5 per MCQ track)</li>
              <li>2-step progressive hints — mental model first, technique second</li>
              <li>Official solutions with explanation after hints</li>
              <li>SQL query quality analysis on correct answers</li>
              <li>Easy mock interviews (unlimited) · 1 medium mock/day</li>
              <li>Streak tracking</li>
            </ul>
            <div className="landing-tier-cta">
              {userPlan === 'free' && <span className="landing-tier-current">Current plan</span>}
            </div>
          </div>

          <div className="landing-tier-col landing-tier-col--featured">
            <div className="landing-tier-col-header">
              <div className="landing-tier-name-row">
                <span className="landing-tier-name">Pro</span>
                <span className="landing-tier-badge">Most popular</span>
              </div>
              <div className="landing-tier-price">
                <span className="landing-tier-price-amount">{p.pro}</span>
                <span className="landing-tier-price-period">{p.period}</span>
              </div>
            </div>
            <ul className="landing-tier-list">
              <li>Everything in Free — no hard cap</li>
              <li>All {ACTIVE_Q} questions, every medium + hard</li>
              <li>Unlimited medium mocks · 3 hard mocks/day</li>
              <li>Fresh mock question bank (questions you haven&rsquo;t seen in practice)</li>
              <li>Post-mock debrief — per-question solutions and concept breakdown</li>
              <li>Weakest concept analysis + drill recommendations</li>
              <li>All learning paths</li>
            </ul>
            <div className="landing-tier-cta">
              {proColCta() === 'current' && <span className="landing-tier-current">Current plan</span>}
              {proColCta() === 'both' && (
                <UpgradeButton tier="pro" source="landing_tier" currency={currency} successPath="/?upgraded=true" />
              )}
              {(proColCta() === 'both' || proColCta() === 'lifetime_only') && (
                <UpgradeButton
                  tier="lifetime_pro"
                  label={proColCta() === 'lifetime_only' ? `Switch to lifetime — ${p.lifetimePro}` : `Lifetime access — ${p.lifetimePro}`}
                  compact
                  className="landing-tier-lifetime-btn"
                  source="landing_tier_lifetime"
                  successPath="/?upgraded=true"
                />
              )}
            </div>
          </div>

          <div className="landing-tier-col">
            <div className="landing-tier-col-header">
              <span className="landing-tier-name">Elite</span>
              <div className="landing-tier-price">
                <span className="landing-tier-price-amount">{p.elite}</span>
                <span className="landing-tier-price-period">{p.period}</span>
              </div>
            </div>
            <ul className="landing-tier-list">
              <li>Everything in Pro</li>
              <li>Unlimited hard mock interviews</li>
              <li>Focus mode — target weak concepts in timed mocks</li>
              <li>Mock history analytics — trends and concept breakdown</li>
              <li>Interview readiness score (per-track 0–100)</li>
              <li>Personalised study plan</li>
              <li>SQL company filter — Meta, Google, Stripe, Airbnb</li>
            </ul>
            <div className="landing-tier-cta">
              {eliteColCta() === 'current' && <span className="landing-tier-current">Current plan</span>}
              {eliteColCta() === 'both' && (
                <UpgradeButton tier="elite" source="landing_tier" currency={currency} successPath="/?upgraded=true" />
              )}
              {(eliteColCta() === 'both' || eliteColCta() === 'lifetime_only') && (
                <UpgradeButton
                  tier="lifetime_elite"
                  label={eliteColCta() === 'lifetime_only' ? `Switch to lifetime — ${p.lifetimeElite}` : `Lifetime access — ${p.lifetimeElite}`}
                  compact
                  className="landing-tier-lifetime-btn"
                  source="landing_tier_lifetime"
                  successPath="/?upgraded=true"
                />
              )}
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}

// ── Section 08: Closer + Footer ─────────────────────────────────────────────
function CloserSection() {
  return (
    <section className="lp-section lp-closer lp-section-rule">
      <div className="lp-inner lp-closer-inner">
        <p className="lp-closer-line">
          Stop recognizing. Start reasoning.
        </p>
        <Link className="btn btn-primary" to="/auth">Start thinking →</Link>
      </div>
    </section>
  );
}

// ── Root export ─────────────────────────────────────────────────────────────
export default function LandingPage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const userPlan = user?.plan ?? 'free';
  const normPlan = userPlan.startsWith('lifetime_') ? userPlan.replace('lifetime_', '') : userPlan;
  const currency = detectCurrency();

  const [dashData, setDashData] = useState(null);
  const [paths, setPaths] = useState([]);
  const [displayedPaths, setDisplayedPaths] = useState([]);
  const [upgradeSuccess, setUpgradeSuccess] = useState(false);

  const [reduced] = useState(() =>
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  const planPillClass = `shell-pill shell-pill-plan shell-pill-plan-${normPlan}`;
  const isPaying = normPlan === 'pro' || normPlan === 'elite';
  const rawPlan = user?.plan ?? 'free';
  const planLabel =
    rawPlan === 'lifetime_elite' ? 'Lifetime Elite' :
    rawPlan === 'lifetime_pro'   ? 'Lifetime Pro'   :
    normPlan === 'elite'         ? 'Elite'           :
    normPlan === 'pro'           ? 'Pro'             : null;
  const planPillNode = user && isPaying && planLabel
    ? <span className={planPillClass}>{planLabel}</span>
    : null;

  useEffect(() => {
    if (!location.search.includes('upgraded=true')) return;
    setUpgradeSuccess(true);
    refreshUser().catch(() => {});
    navigate({ pathname: '/' }, { replace: true });
  }, [location.search, navigate, refreshUser]);

  useEffect(() => {
    if (user) {
      api.get('/dashboard').then(r => setDashData(r.data)).catch(() => {});
    } else {
      setDashData(null);
    }
  }, [user]);

  useEffect(() => {
    api.get('/paths').then(r => {
      setPaths(r.data);
      const shuffled = [...r.data].sort(() => Math.random() - 0.5);
      setDisplayedPaths(shuffled.slice(0, 4));
    }).catch(() => {});
  }, []);

  const shufflePaths = useCallback(() => {
    setDisplayedPaths([...paths].sort(() => Math.random() - 0.5).slice(0, 4));
  }, [paths]);

  const showPricing = !['lifetime_elite'].includes(userPlan);

  return (
    <>
      <Helmet>
        <title>datathink — SQL, Python &amp; Data Interview Practice</title>
        <meta name="description" content="Practice SQL, Python, Pandas, PySpark, and Data Engineering interview questions. 7 tracks, real execution, instant feedback, and curated learning paths for data professionals." />
        <meta property="og:title" content="datathink — SQL, Python &amp; Data Interview Practice" />
        <meta property="og:description" content="7 tracks covering the full data interview curriculum — SQL, Python, Pandas, PySpark, Data Engineering, and more. Real execution, instant feedback." />
        <meta property="og:url" content="https://datathink.co/" />
        <meta property="og:image" content="https://datathink.co/og-image.png" />
        <link rel="canonical" href="https://datathink.co/" />
      </Helmet>

      <Topbar userExtras={planPillNode} />

      <main className="lp-page" id="landing-top">
        {upgradeSuccess && (
          <div className="landing-upgrade-banner">
            Upgrade confirmed. Your access has been updated.
          </div>
        )}

        {/* 01 HERO */}
        <HeroSection user={user} dashData={dashData} reduced={reduced} />

        {/* 02 + 03: THESIS + WRONG/RIGHT — logged-out only */}
        {!user && (
          <>
            <ThesisSection />
            <WrongRightSection />
          </>
        )}

        {/* 04 ROLE SELECTOR */}
        <RoleSelectorSection dashData={dashData} />

        {/* 05 PROOF STRIP */}
        <ProofStripSection />

        {/* 06 TRACKS INDEX */}
        <TracksIndexSection />

        {/* Paths — shown for everyone */}
        {displayedPaths.length > 0 && (
          <section className="lp-section lp-section-rule lp-paths">
            <div className="lp-inner">
              <Reveal>
                <div className="lp-paths-header">
                  <div>
                    <p className="lp-section-index">+&ensp;LEARNING PATHS</p>
                    <h2 className="lp-section-h2">Guided progressions.</h2>
                    <p className="lp-section-sub">Curated question sequences that build real interview reasoning, track by track.</p>
                  </div>
                  <button className="landing-paths-shuffle" onClick={shufflePaths} aria-label="Shuffle learning paths">
                    ⇄ Shuffle
                  </button>
                </div>
              </Reveal>
              <div className="landing-paths-grid">
                {displayedPaths.map(p => <PathProgressCard key={p.slug} path={p} />)}
              </div>
            </div>
          </section>
        )}

        {/* 07 PRICING */}
        {showPricing && (
          <PricingSection userPlan={normPlan} currency={currency} />
        )}

        {/* 08 CLOSER (logged-out only) */}
        {!user && <CloserSection />}

        <footer className="landing-footer">
          <div className="landing-footer-inner">
            <span className="landing-footer-copy">&copy; 2026 datathink</span>
            <nav className="landing-footer-links" aria-label="Legal">
              <Link to="/faq">FAQ</Link>
              <Link to="/privacy" state={{ backgroundLocation: location }}>Privacy Policy</Link>
              <Link to="/terms" state={{ backgroundLocation: location }}>Terms &amp; Conditions</Link>
              <Link to="/refund-policy" state={{ backgroundLocation: location }}>Refund Policy</Link>
              <Link to="/contact" state={{ backgroundLocation: location }}>Contact Us</Link>
            </nav>
          </div>
        </footer>
      </main>
    </>
  );
}
