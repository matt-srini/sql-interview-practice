import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import { ALL_TRACK_SLUGS, TRACK_SLUGS } from '../trackRegistry';
import { useCatalogCounts } from '../contexts/CatalogCountsContext';
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
    tagline: 'ML · statistical inference · Python for modelling',
    tracks: ['ml-fundamentals', 'statistics', 'experimentation', 'python', 'sql'],
  },
];

// ── Hero IDE content ────────────────────────────────────────────────────────
const IDE_TRACKS = [
  {
    slug: 'sql',
    label: 'SQL',
    color: '#5B6AF0',
    fname: 'dau_trend.sql',
    badge: 'SQL · DuckDB',
    code: `SELECT\n  event_date,\n  ROUND(AVG(dau) OVER (\n    ORDER BY event_date\n    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW\n  ), 0) AS rolling_7d_avg\nFROM daily_active_users\nORDER BY event_date DESC\nLIMIT 3;`,
    type: 'table',
    cols: ['event_date', 'rolling_7d_avg'],
    rows: [
      ['2026-05-27', '48,210'],
      ['2026-05-26', '47,850'],
      ['2026-05-25', '46,430'],
    ],
  },
  {
    slug: 'python',
    label: 'Python',
    color: '#2D9E6B',
    fname: 'sessionize_events.py',
    badge: 'Python · Sandbox',
    code: `def solve(events, gap_minutes=30):\n    sessions = 1\n    for prev, event in zip(events, events[1:]):\n        if event['ts'] - prev['ts'] > gap_minutes * 60:\n            sessions += 1\n    return sessions`,
    type: 'tests',
    tests: [
      { label: 'test_30_min_gap',      passed: true, ms: '0.3' },
      { label: 'test_cross_midnight',  passed: true, ms: '0.4' },
      { label: 'test_sparse_activity', passed: true, ms: '1.1' },
    ],
  },
  {
    slug: 'python-data',
    label: 'Pandas',
    color: '#C47F17',
    fname: 'channel_revenue.py',
    badge: 'Pandas · Sandbox',
    code: `def solve(orders):\n    completed = orders[orders['status'] == 'completed'].copy()\n    return (\n        completed.groupby('acquisition_channel', as_index=False)['net_amount']\n        .sum()\n        .sort_values('net_amount', ascending=False)\n    )`,
    type: 'table',
    cols: ['acquisition_channel', 'net_amount'],
    rows: [
      ['organic', '$84,200'],
      ['paid_search', '$61,480'],
      ['partner', '$43,900'],
    ],
  },
  {
    slug: 'pyspark',
    label: 'PySpark',
    color: '#D94F3D',
    fname: 'transformations.md',
    badge: 'PySpark · Reasoning',
    code: null,
    type: 'conceptual',
    question: 'A Spark job is bottlenecked on shuffle after a large join, then groupBy. What should you test first?',
    options: ['Increase executor memory', 'Broadcast the raw events table', 'Pre-aggregate before the join', 'Coalesce to one partition'],
    correct: 2,
  },
  {
    slug: 'data-engineering',
    label: 'Data Eng',
    color: '#B9762B',
    fname: 'pipeline_reliability.md',
    badge: 'Data Eng · Reasoning',
    code: null,
    type: 'conceptual',
    question: 'A daily warehouse load reruns after upstream lag and duplicates yesterday\'s rows. What is missing?',
    options: ['A higher retry limit', 'An idempotent merge keyed by business grain', 'More worker nodes', 'Another cron trigger'],
    correct: 1,
  },
  {
    slug: 'data-modeling',
    label: 'Modeling',
    color: '#3F8E8C',
    fname: 'fact_grain.md',
    badge: 'Modeling · Reasoning',
    code: null,
    type: 'conceptual',
    question: 'You need daily revenue by customer segment, but orders contain many items and promotions. What do you define first?',
    options: ['The warehouse tool', 'The fact table grain', 'The dashboard refresh time', 'The semantic layer name'],
    correct: 1,
  },
  {
    slug: 'statistics',
    label: 'Statistics',
    color: '#7A5AF0',
    fname: 'bayes_ppv.py',
    badge: 'Statistics · Numerical',
    code: `def solve(prevalence, sensitivity, specificity):\n    p_pos = (\n        sensitivity * prevalence\n        + (1 - specificity) * (1 - prevalence)\n    )\n    return round(sensitivity * prevalence / p_pos, 4)`,
    type: 'tests',
    tests: [
      { label: 'test_rare_disease',    passed: true, ms: '0.2' },
      { label: 'test_high_prevalence', passed: true, ms: '0.2' },
      { label: 'test_perfect_spec',    passed: true, ms: '0.1' },
    ],
  },
  {
    slug: 'ml-fundamentals',
    label: 'ML',
    color: '#E0456A',
    fname: 'production_gap.md',
    badge: 'ML · Reasoning',
    code: null,
    type: 'conceptual',
    question: 'Offline AUC is 0.96, but production drops to 0.61 right after launch. What do you suspect first?',
    options: ['Training-serving skew or leakage', 'Too few trees', 'Batch size too small', 'Learning rate too low'],
    correct: 0,
  },
  {
    slug: 'experimentation',
    label: 'Experiment',
    color: '#0EA5E9',
    fname: 'novelty_effect.md',
    badge: 'Experiment · Reasoning',
    code: null,
    type: 'conceptual',
    question: 'Week 1 shows +5% clicks, week 3 is flat, and the treatment changes a homepage habit. What pattern fits best?',
    options: ['Novelty effect', 'Perfect randomization', 'Lower variance only', 'Guaranteed long-term lift'],
    correct: 0,
  },
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
  const [activeIdx, setActiveIdx] = useState(0);
  const [visible, setVisible]     = useState(true);
  const sqlAnimDoneRef  = useRef(reduced);
  const pauseUntilRef   = useRef(0);
  const timerRef        = useRef(null);

  const sqlTrack = IDE_TRACKS[0];
  const SQL_TOTAL = sqlTrack.code.length;
  const isSQL = activeIdx === 0;

  // SQL animation state
  const [typedLen, setTypedLen]       = useState(reduced ? SQL_TOTAL : 0);
  const [phase, setPhase]             = useState(reduced ? 'done' : 'typing');
  const [visibleRows, setVisibleRows] = useState(reduced ? sqlTrack.rows.length : 0);
  const [flashIdx, setFlashIdx]       = useState(null);

  const animActive = isSQL && !sqlAnimDoneRef.current;

  useEffect(() => {
    if (!animActive || phase !== 'typing') return;
    if (typedLen >= SQL_TOTAL) { setTimeout(() => setPhase('running'), 350); return; }
    const t = setTimeout(() => setTypedLen(n => n + 1), 26);
    return () => clearTimeout(t);
  }, [animActive, phase, typedLen, SQL_TOTAL]);

  useEffect(() => {
    if (!animActive || phase !== 'running') return;
    const t = setTimeout(() => setPhase('streaming'), 550);
    return () => clearTimeout(t);
  }, [animActive, phase]);

  useEffect(() => {
    if (!animActive || phase !== 'streaming') return;
    if (visibleRows >= sqlTrack.rows.length) {
      setPhase('done');
      sqlAnimDoneRef.current = true;
      return;
    }
    const t = setTimeout(() => {
      const idx = visibleRows;
      setVisibleRows(n => n + 1);
      setFlashIdx(idx);
      setTimeout(() => setFlashIdx(null), 180);
    }, 55);
    return () => clearTimeout(t);
  }, [animActive, phase, visibleRows, sqlTrack.rows.length]);

  // Auto-advance after SQL animation finishes (or immediately when reduced)
  useEffect(() => {
    const isReady = phase === 'done' || reduced;
    if (!isReady) return;
    const initialDelay = setTimeout(() => {
      timerRef.current = setInterval(() => {
        if (Date.now() < pauseUntilRef.current) return;
        setVisible(false);
        setTimeout(() => {
          setActiveIdx(i => (i + 1) % IDE_TRACKS.length);
          setVisible(true);
        }, 280);
      }, 3500);
    }, 2200);
    return () => {
      clearTimeout(initialDelay);
      clearInterval(timerRef.current);
    };
  }, [phase, reduced]); // eslint-disable-line react-hooks/exhaustive-deps

  const activeTrack = IDE_TRACKS[activeIdx];
  const showRunning = isSQL && phase === 'running';

  const handleDotClick = (idx) => {
    pauseUntilRef.current = Date.now() + 6000;
    setVisible(false);
    setTimeout(() => { setActiveIdx(idx); setVisible(true); }, 280);
  };

  return (
    <div
      className="lp-ide"
      aria-label="Live query execution preview"
      aria-hidden="true"
      onMouseEnter={() => { pauseUntilRef.current = Infinity; }}
      onMouseLeave={() => { pauseUntilRef.current = 0; }}
    >
      {/* Chrome bar */}
      <div className="lp-ide-chrome">
        <span className="lp-ide-dots"><i /><i /><i /></span>
        <span className="lp-ide-fname">{activeTrack.fname}</span>
        <span
          className="lp-ide-badge"
          style={{ background: `${activeTrack.color}33`, color: activeTrack.color }}
        >
          {activeTrack.badge}
        </span>
      </div>

      {/* Body — fixed height, crossfades on track change */}
      <div className="lp-ide-body" style={{ opacity: visible ? 1 : 0 }}>
        {activeTrack.code && (
          <pre className="lp-ide-query"><code>
            {isSQL ? (
              Array.from(activeTrack.code).map((ch, i) => (
                <span key={i} style={i >= typedLen ? { color: 'transparent' } : undefined}>{ch}</span>
              ))
            ) : (
              activeTrack.code
            )}
            {isSQL && phase !== 'done' && <span className="lp-ide-cursor" />}
          </code></pre>
        )}

        <div className="lp-ide-result" style={{ position: 'relative' }}>
          {showRunning && (
            <p className="lp-ide-running" style={{ position: 'absolute', marginTop: '-4px' }}>Running…</p>
          )}

          {activeTrack.type === 'table' && (
            <>
              <table>
                <thead>
                  <tr>{activeTrack.cols.map(c => <th key={c}>{c}</th>)}</tr>
                </thead>
                <tbody>
                  {activeTrack.rows.map((row, i) => (
                    <tr
                      key={i}
                      className={flashIdx === i ? 'lp-ide-row--flash' : ''}
                      style={{
                        visibility: isSQL
                          ? (i < visibleRows ? 'visible' : 'hidden')
                          : 'visible',
                      }}
                    >
                      {row.map((cell, j) => <td key={j}>{cell}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p
                className="lp-ide-rowcount"
                style={{ visibility: isSQL ? (phase === 'done' ? 'visible' : 'hidden') : 'visible' }}
              >
                {activeTrack.rows.length} rows · 0 errors
              </p>
            </>
          )}

          {activeTrack.type === 'tests' && (
            <>
              <div className="lp-ide-tests">
                {activeTrack.tests.map((tc, i) => (
                  <div key={i} className={`lp-ide-test lp-ide-test--${tc.passed ? 'pass' : 'fail'}`}>
                    <span className="lp-ide-test-icon">{tc.passed ? '✓' : '✗'}</span>
                    <span className="lp-ide-test-label">{tc.label}</span>
                    <span className="lp-ide-test-ms">{tc.ms} ms</span>
                  </div>
                ))}
              </div>
              <p className="lp-ide-rowcount">
                {activeTrack.tests.filter(t => t.passed).length} / {activeTrack.tests.length} tests passed
              </p>
            </>
          )}

          {activeTrack.type === 'conceptual' && (
            <div className="lp-ide-mcq">
              <p className="lp-ide-mcq-q">{activeTrack.question}</p>
              <div className="lp-ide-mcq-opts">
                {activeTrack.options.map((opt, i) => (
                  <div
                    key={i}
                    className={`lp-ide-mcq-opt${i === activeTrack.correct ? ' lp-ide-mcq-opt--correct' : ''}`}
                  >
                    <span className="lp-ide-mcq-letter">{String.fromCharCode(65 + i)}</span>
                    {opt}
                    {i === activeTrack.correct && <span className="lp-ide-mcq-check">✓</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Dot navigation */}
      <div className="lp-ide-nav">
        {IDE_TRACKS.map((t, i) => (
          <button
            key={t.slug}
            className={`lp-ide-nav-dot${i === activeIdx ? ' lp-ide-nav-dot--active' : ''}`}
            style={i === activeIdx ? { background: activeTrack.color } : undefined}
            onClick={() => handleDotClick(i)}
          />
        ))}
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
          <p className="lp-eyebrow">For data professionals — and those becoming one.</p>
          <h1 className="lp-hero-h1">
            Develop the reasoning that makes you effective with data.
          </h1>
          <p className="lp-hero-sub">
            Nine tracks — SQL, Python, ML, statistics, data engineering, and more — on real engines. The kind of thinking that holds up years into the job — and if it also makes you exceptional in interviews, that's a consequence, not the goal.
          </p>
          <div className="lp-hero-actions">
            <Link className="btn btn-primary" to="/sample">Try a free sample →</Link>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                const el = document.getElementById('lp-roles');
                if (!el) return;
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }}
            >
              Find your role ↓
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
      copy: 'SQL runs against a real DuckDB engine. Python executes in an isolated sandbox. For reasoning tracks — ML, statistics, data engineering — real scenarios test your judgment, not pattern recall.',
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
            Pick your role and see where to focus first.
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
function ProofStripSection() {
  const counts = useCatalogCounts();
  const practiceTotal = TRACK_SLUGS.reduce((s, slug) => s + (counts[slug]?.total ?? 0), 0);
  const ref = useRef(null);
  const inView = useInView(ref, '-5%');
  const reduced = typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const qCount = useCountUp(practiceTotal, 700, reduced || inView);
  const trackCount = useCountUp(ALL_TRACK_SLUGS.length, 500, reduced || inView);

  const STATS = [
    { num: trackCount, label: 'tracks' },
    { num: `${qCount}+`, label: 'engineered questions' },
    { text: 'real DuckDB execution' },
    { text: 'timed benchmarks + weak-area coaching' },
    { text: 'exclusive mock question bank' },
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
          Reasoning patterns drawn from real practitioner work and real interview shapes at Meta, Stripe, Airbnb, Google, Amazon, and Uber.
        </p>
      </div>
    </section>
  );
}

// ── Section 06: Tracks index ────────────────────────────────────────────────
function TracksIndexSection() {
  const counts = useCatalogCounts();
  const practiceTotal = TRACK_SLUGS.reduce((s, slug) => s + (counts[slug]?.total ?? 0), 0);
  const FORMAT_LABELS = {
    sql:                'SQL · DuckDB',
    python:             'Python · sandbox',
    'python-data':      'Pandas · sandbox',
    pyspark:            'reasoning · predict output',
    'data-engineering': 'reasoning · scenario',
    'data-modeling':    'reasoning · schema design',
    statistics:         'conceptual + numerical',
    experimentation:    'reasoning · scenario',
  };

  return (
    <section className="lp-section lp-tracks lp-section-rule" id="lp-tracks">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">06&ensp;/&ensp;ALL TRACKS</p>
          <h2 className="lp-section-h2">The full curriculum.</h2>
          <p className="lp-tracks-editorial">
            Not 2,000. Just the <span className="lp-tracks-editorial-n">{practiceTotal || '…'}</span> that actually matter.
          </p>
        </Reveal>
        <div className="lp-tracks-list" role="list">
          {ALL_TRACK_SLUGS.map((slug, i) => {
            const meta = TRACK_META[slug];
            const isActive = TRACK_SLUGS.includes(slug);
            const totalQ = counts[slug]?.total;
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
                    {totalQ ? <span className="lp-track-count">{totalQ} q</span> : null}
                    <span className="lp-track-format">{FORMAT_LABELS[slug] ?? meta.tagline}</span>
                  </div>
                  {isActive ? (
                    <div className="lp-track-actions" style={{ '--row-color': meta.color }}>
                      <Link
                        to={`/practice/${slug}`}
                        className="lp-track-enter"
                        aria-label={`Open ${meta.label} track`}
                      >
                        Enter →
                      </Link>
                      <Link
                        to={`/sample/${slug}/easy`}
                        className="lp-track-sample"
                        aria-label={`Try a ${meta.label} sample`}
                      >
                        Try sample →
                      </Link>
                    </div>
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

// ── Section 06.5: Learning paths showcase ───────────────────────────────────
// Pitches the curriculum's STRUCTURE — one track's graded arc shown as a
// connected spine, making the foundational→advanced climb visible — and its
// BREADTH (every track with its path count), then funnels to /learn, the
// curriculum front door. It never deep-links into a single path (the old
// "random 4 + shuffle" did, bypassing /learn); the only leaf link is the
// returning-user resume hook, where deep-linking is the correct destination.
const _PATH_LEVEL_ORDER = { foundational: 0, intermediate: 1, advanced: 2 };
const _FEATURED_PATH_TRACK = 'sql'; // flagship arc; swap by changing this slug

function PathsShowcaseSection({ paths, user }) {
  if (!paths.length) return null;

  const totalPaths = paths.length;
  const trackCounts = TRACK_SLUGS
    .map(slug => ({ slug, meta: TRACK_META[slug], count: paths.filter(p => p.topic === slug).length }))
    .filter(t => t.count > 0);
  const trackCount = trackCounts.length;

  const featMeta = TRACK_META[_FEATURED_PATH_TRACK];
  const featuredArc = paths
    .filter(p => p.topic === _FEATURED_PATH_TRACK)
    .slice()
    .sort((a, b) =>
      (_PATH_LEVEL_ORDER[a.level] ?? 3) - (_PATH_LEVEL_ORDER[b.level] ?? 3) ||
      (a.display_order ?? 999) - (b.display_order ?? 999)
    );
  const SPINE_MAX = 5; // first 5 by (level, display_order) span all three levels
  const spine = featuredArc.slice(0, SPINE_MAX);
  const moreCount = Math.max(0, featuredArc.length - SPINE_MAX);

  // Returning users with an unfinished path get a resume hook; first-timers
  // get the pitch. Furthest-along (highest completion ratio) wins.
  const resume = user
    ? paths
        .filter(p => p.solved_count >= 1 && p.solved_count < p.question_count)
        .sort((a, b) => (b.solved_count / b.question_count) - (a.solved_count / a.question_count))[0]
    : null;

  return (
    <section className="lp-section lp-section-rule lp-paths" id="lp-paths">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">+&ensp;LEARNING PATHS</p>
          <h2 className="lp-section-h2">Know what to practice, and in what order.</h2>
          <p className="lp-section-sub">
            Each track is a graded sequence — foundational patterns first, then the intermediate
            and advanced reasoning that builds on them. {totalPaths} guided paths across {trackCount} tracks.
          </p>
        </Reveal>

        <div className="lp-paths-showcase">
          {/* LEFT — featured arc: the foundational→advanced climb made visible */}
          <Reveal className="lp-paths-arc-wrap">
            <Link
              to={`/learn/${_FEATURED_PATH_TRACK}`}
              className="lp-paths-arc"
              style={{ '--arc-color': featMeta.color }}
            >
              <div className="lp-paths-arc-head">
                <span className="lp-track-dot" style={{ background: featMeta.color }} aria-hidden="true" />
                <span className="lp-paths-arc-track">{featMeta.label}</span>
                <span className="lp-paths-arc-tag">{featuredArc.length}-path sequence</span>
              </div>
              <ol className="lp-paths-spine">
                {spine.map((p, i) => (
                  <li key={p.slug} className="lp-paths-step">
                    <span className="lp-paths-step-num">{i + 1}</span>
                    <span className="lp-paths-step-body">
                      <span className="lp-paths-step-title">{p.title}</span>
                      <span className={`lp-paths-step-level lp-paths-step-level--${p.level}`}>{p.level}</span>
                    </span>
                  </li>
                ))}
              </ol>
              <span className="lp-paths-arc-more">
                {moreCount > 0 ? `+${moreCount} more in ${featMeta.label}` : `See the ${featMeta.label} arc`} →
              </span>
            </Link>
          </Reveal>

          {/* RIGHT — breadth: every track with its path count, each a door to /learn/:topic */}
          <Reveal className="lp-paths-breadth" delay={80}>
            <div className="lp-paths-breadth-stat">
              <strong>{trackCount}</strong> tracks
              <span className="lp-paths-breadth-sep">·</span>
              <strong>{totalPaths}</strong> guided paths
            </div>
            <ul className="lp-paths-tracklist" role="list">
              {trackCounts.map(({ slug, meta, count }) => (
                <li key={slug}>
                  <Link
                    to={`/learn/${slug}`}
                    className="lp-paths-trackchip"
                    style={{ '--chip-color': meta.color }}
                  >
                    <span className="lp-track-dot" style={{ background: meta.color }} aria-hidden="true" />
                    <span className="lp-paths-trackchip-name">{meta.label}</span>
                    <span className="lp-paths-trackchip-count">{count} path{count === 1 ? '' : 's'}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>

        {/* FRONT DOOR — one primary CTA to /learn (+ resume hook for returning users) */}
        <Reveal className="lp-paths-cta">
          <Link to="/learn" className="lp-paths-cta-primary">Explore all paths →</Link>
          {resume && (
            <Link to={`/learn/${resume.topic}/${resume.slug}`} className="lp-paths-cta-resume">
              Continue: {resume.title} →
            </Link>
          )}
        </Reveal>
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

  const counts = useCatalogCounts();
  const ACTIVE_Q = TRACK_SLUGS.reduce((s, slug) => s + (counts[slug]?.total ?? 0), 0);
  const FREE_EASY = TRACK_SLUGS
    .filter(s => counts[s]?.easy)
    .map(s => `${counts[s].easy} ${TRACK_META[s].label}`)
    .join(' · ');

  return (
    <section className="lp-section lp-section-rule" id="landing-pricing">
      <div className="lp-inner">
        <Reveal>
          <p className="lp-section-index">07&ensp;/&ensp;PRICING</p>
          <h2 className="lp-section-h2">Practice free. Prepare seriously.</h2>
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
              <li>All easy questions{FREE_EASY ? ` (${FREE_EASY})` : ''}</li>
              <li>Medium + hard unlock as you solve (hard cap: 8 per code track, 5 per reasoning track)</li>
              <li>2-step progressive hints — mental model first, technique second</li>
              <li>Official solutions with explanation after hints</li>
              <li>SQL query quality analysis on correct answers</li>
              <li>1 easy benchmark per rolling 7 days</li>
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
              <li>Everything in Free — no hard cap on practice</li>
              <li>All {ACTIVE_Q || '…'} questions, every medium + hard</li>
              <li>3 benchmark mocks per day · 3 custom drills per day</li>
              <li>Exclusive mock-only question bank — questions reserved for mock sessions, never shown in practice</li>
              <li>Detailed mock history, per-question solutions, and concept breakdowns</li>
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
              <li>Unlimited mock sessions — benchmarks, drills, and Interview Loop</li>
              <li><strong>Interview Loop</strong> — chain-driven sessions where each follow-up pivots like a real interviewer (scale, business rule, data quality, ambiguity…)</li>
              <li>Focus mode — target weak concepts in timed mocks</li>
              <li>Per-dimension weak-spot detection (what kinds of pivots break you)</li>
              <li>Cross-session trend analytics + readiness score (per-track 0–100)</li>
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
        <Link className="btn btn-primary" to="/sample">Try a free sample →</Link>
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

  // Scroll to a named section delivered via router state — used by TierBanner,
  // InsightStrip, AccountPage, and the path sidebar so they can land at a section
  // without leaving a hash or query param in the URL.
  useEffect(() => {
    const target = location.state?.scrollTo;
    if (!target) return;
    try { window.history.replaceState({ ...window.history.state, usr: null }, ''); } catch {}
    const scroll = () => {
      const el = document.getElementById(target);
      if (!el) return;
      const top = el.getBoundingClientRect().top + window.scrollY - 88;
      window.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    };
    const t1 = setTimeout(scroll, 220);
    const t2 = setTimeout(scroll, 500);
    const t3 = setTimeout(scroll, 1200);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (user) {
      api.get('/dashboard').then(r => setDashData(r.data)).catch(() => {});
    } else {
      setDashData(null);
    }
  }, [user]);

  useEffect(() => {
    api.get('/paths').then(r => setPaths(r.data)).catch(() => {});
  }, []);

  const showPricing = !['lifetime_elite'].includes(userPlan);

  return (
    <>
      <Helmet>
        <title>datathink — SQL, Python &amp; Data Interview Practice</title>
        <meta name="description" content="Develop the data-professional reasoning that matters on the job — across SQL, Python, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML, and Experimentation. Real datasets, real execution, real interview shapes." />
        <meta property="og:title" content="datathink — SQL, Python &amp; Data Interview Practice" />
        <meta property="og:description" content="9 tracks training the reasoning that makes data professionals genuinely effective — SQL, Python, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML, Experimentation. Interview success follows." />
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
        <PathsShowcaseSection paths={paths} user={user} />

        {/* 07 PRICING */}
        {showPricing && (
          <PricingSection userPlan={userPlan} currency={currency} />
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
