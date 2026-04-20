import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import TrackProgressBar from '../components/TrackProgressBar';
import PathProgressCard from '../components/PathProgressCard';
import Topbar from '../components/Topbar';
import LoggedInWelcome from '../components/LoggedInWelcome';
import UpgradeButton from '../components/UpgradeButton';
import OnboardingTooltip from '../components/OnboardingTooltip';
import { highlightCode } from './landingShowcaseHighlight';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

const TRACK_DIFFICULTIES = {
  sql:           { easy: 32, medium: 34, hard: 29 },
  python:        { easy: 30, medium: 29, hard: 24 },
  'python-data': { easy: 29, medium: 30, hard: 23 },
  pyspark:       { easy: 38, medium: 30, hard: 22 },
};

// Total easy questions across all tracks (used in pricing copy)
const TOTAL_EASY = Object.values(TRACK_DIFFICULTIES).reduce((s, d) => s + d.easy, 0);
// Total questions across all tracks
const TOTAL_QUESTIONS = Object.values(TRACK_DIFFICULTIES).reduce((s, d) => s + d.easy + d.medium + d.hard, 0);

const SAMPLE_TIERS = {
  sql: [
    { difficulty: 'easy', title: 'Warm-up joins', copy: 'Three approachable query prompts on filters, joins, and aggregates.' },
    { difficulty: 'medium', title: 'Interview core', copy: 'A mid-tier SQL set focused on grouping, window logic, and cleaner result shaping.' },
    { difficulty: 'hard', title: 'Stretch round', copy: 'Three harder SQL prompts to pressure-test precision and sequencing.' },
  ],
  python: [
    { difficulty: 'easy', title: 'Warm-up problems', copy: 'Three algorithm samples with light control flow and array/string handling.' },
    { difficulty: 'medium', title: 'Core patterns', copy: 'Interview-style Python samples covering maps, traversal, and common data structures.' },
    { difficulty: 'hard', title: 'Stretch problems', copy: 'Tighter Python prompts that reward clean reasoning and edge-case handling.' },
  ],
  'python-data': [
    { difficulty: 'easy', title: 'DataFrame warm-up', copy: 'Three pandas samples for selection, filtering, and tidy output shaping.' },
    { difficulty: 'medium', title: 'Analysis patterns', copy: 'Practice merge, grouping, and transformation patterns used in real interviews.' },
    { difficulty: 'hard', title: 'Wrangling stretch', copy: 'A tougher pandas set focused on sequencing, normalization, and precision.' },
  ],
  pyspark: [
    { difficulty: 'easy', title: 'Spark basics', copy: 'Three PySpark samples covering execution basics, APIs, and conceptual foundations.' },
    { difficulty: 'medium', title: 'Distributed thinking', copy: 'A mid-tier set on shuffles, partitioning, and practical transformation choices.' },
    { difficulty: 'hard', title: 'Systems stretch', copy: 'Harder PySpark samples for optimization instincts and architecture judgment.' },
  ],
};

const SHOWCASE_CARDS = [
  {
    topic: 'sql',
    fileName: 'rolling_revenue.sql',
    language: 'sql',
    difficulty: 'medium',
    title: '7-Day Rolling Revenue',
    briefParagraph:
      "For each day, compute the sum of order revenue over the past 7 days (including today). The output should align one row per order_date in ascending order.",
    returnsNote: 'Return: order_date, daily_revenue, rolling_7d_revenue',
    concepts: ['window functions', 'rolling aggregates'],
    solutionCode: `SELECT
  order_date,
  SUM(total_amount) AS daily_revenue,
  SUM(SUM(total_amount)) OVER (
    ORDER BY order_date
    ROWS BETWEEN 6 PRECEDING
             AND CURRENT ROW
  ) AS rolling_7d_revenue
FROM orders
GROUP BY order_date
ORDER BY order_date;`,
  },
  {
    topic: 'python',
    fileName: 'trapping_rain_water.py',
    language: 'python',
    difficulty: 'hard',
    title: 'Trapping Rain Water',
    briefParagraph:
      "Given an elevation map of unit-width bars, compute the total rainwater that can be trapped between them. Solve it in O(n) time and O(1) space.",
    returnsNote: 'Two pointers · O(n) time · O(1) space',
    concepts: ['two pointers', 'amortized analysis'],
    solutionCode: `def solve(heights):
    if not heights:
        return 0
    left, right = 0, len(heights) - 1
    left_max = right_max = 0
    water = 0
    while left < right:
        if heights[left] < heights[right]:
            left_max = max(left_max, heights[left])
            water += left_max - heights[left]
            left += 1
        else:
            right_max = max(right_max, heights[right])
            water += right_max - heights[right]
            right -= 1
    return water`,
  },
  {
    topic: 'python-data',
    fileName: 'email_domain.py',
    language: 'python',
    difficulty: 'easy',
    title: 'Extract Email Domain',
    briefParagraph:
      "Drop rows with a null email, then add an email_domain column holding everything after the @. Return the DataFrame with the new column appended.",
    returnsNote: 'Return: original columns + email_domain',
    concepts: ['string accessors', 'null handling'],
    solutionCode: `def solve(df_users):
    result = df_users.dropna(subset=['email']).copy()
    result['email_domain'] = (
        result['email'].str.split('@').str[1]
    )
    return result.reset_index(drop=True)`,
  },
  {
    topic: 'pyspark',
    fileName: 'coalesce_vs_repartition.py',
    language: 'python',
    difficulty: 'medium',
    title: 'coalesce vs repartition',
    briefParagraph:
      "You need to reduce a DataFrame from 200 partitions to 10 before writing. Which operation avoids a full shuffle, and when does each one matter?",
    returnsNote: 'coalesce = narrow · repartition = wide (shuffle)',
    concepts: ['partitions', 'shuffle tradeoffs'],
    solutionCode: `# coalesce(n) — merges partitions locally, no full
# shuffle. Best when REDUCING partition count.
df.coalesce(10).write.parquet(path)

# repartition(n) — full shuffle, even distribution.
# Use when INCREASING count or when data is skewed.
df.repartition(10, 'user_id')`,
  },
];

const SHOWCASE_ROTATE_MS = 8000;
const LANDING_ONBOARDING_KEY = 'landingOnboardingSeen-v1';

export default function LandingPage() {
  const { user, logout } = useAuth();
  const userPlan = user?.plan ?? 'free';

  // What CTA state to show in the Pro column:
  //   'current'      → user is on lifetime_pro (highest Pro billing, no action needed)
  //   'lifetime_only'→ user is on monthly pro (can still switch to lifetime)
  //   'both'         → user is on free (show monthly + lifetime buttons)
  //   'none'         → user is on elite/lifetime_elite (Pro is below their tier)
  function proColCta() {
    if (userPlan === 'lifetime_pro')  return 'current';
    if (userPlan === 'pro')           return 'lifetime_only';
    if (userPlan === 'free')          return 'both';
    return 'none'; // elite / lifetime_elite
  }

  // What CTA state to show in the Elite column:
  //   'current'      → user is on lifetime_elite (can't go higher)
  //   'lifetime_only'→ user is on monthly elite (can switch to lifetime)
  //   'both'         → user is on free / pro / lifetime_pro (show both buttons)
  function eliteColCta() {
    if (userPlan === 'lifetime_elite') return 'current';
    if (userPlan === 'elite')          return 'lifetime_only';
    return 'both';
  }

  const [dashData, setDashData] = useState(null);
  const [activeTab, setActiveTab] = useState(
    () => localStorage.getItem('landingActiveTab') || 'sql'
  );
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => (
    typeof window !== 'undefined'
    && window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  ));

  const showcaseRef = useRef(null);
  const [showcaseActiveIndex, setShowcaseActiveIndex] = useState(0);
  const [showcaseInView, setShowcaseInView] = useState(false);
  const [showcasePaused, setShowcasePaused] = useState(false);
  const [onboardingOpen, setOnboardingOpen] = useState(false);

  const showcaseTabRefs = useRef([]);
  const showcaseDotRefs = useRef([]);

  const [paths, setPaths] = useState([]);
  const [displayedPaths, setDisplayedPaths] = useState([]);

  function pickRandom(arr, n) {
    const shuffled = [...arr].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, n);
  }

  const shufflePaths = () => setDisplayedPaths(pickRandom(paths, 4));

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = (event) => setPrefersReducedMotion(event.matches);
    if (media.addEventListener) media.addEventListener('change', onChange);
    else media.addListener(onChange);
    return () => {
      if (media.removeEventListener) media.removeEventListener('change', onChange);
      else media.removeListener(onChange);
    };
  }, []);

  useEffect(() => {
    if (user) {
      api.get('/dashboard').then((res) => setDashData(res.data)).catch(() => {});
      return;
    }
    setDashData(null);
  }, [user]);

  useEffect(() => {
    api.get('/paths').then(r => {
      setPaths(r.data);
      setDisplayedPaths(pickRandom(r.data, 4));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    let timer;
    try {
      const seen = localStorage.getItem(LANDING_ONBOARDING_KEY);
      if (!seen) timer = setTimeout(() => setOnboardingOpen(true), 10000);
    } catch {
      timer = setTimeout(() => setOnboardingOpen(true), 10000);
    }
    return () => clearTimeout(timer);
  }, []);

  // Scroll to hash on mount (e.g. /#landing-tracks from back arrow)
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash) return;
    const id = hash.slice(1);
    // Two attempts: one after paint, one after React Router scroll restoration
    const scroll = () => {
      const el = document.getElementById(id);
      if (el) window.scrollTo({ top: el.offsetTop - 16, behavior: 'smooth' });
    };
    const t1 = setTimeout(scroll, 100);
    const t2 = setTimeout(scroll, 400);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  // Auto-rotate the IDE tabs — runs only when section is in view and not paused.
  useEffect(() => {
    if (!showcaseInView || showcasePaused || prefersReducedMotion) return;
    const id = setInterval(() => {
      setShowcaseActiveIndex((prev) => (prev + 1) % SHOWCASE_CARDS.length);
    }, SHOWCASE_ROTATE_MS);
    return () => clearInterval(id);
  }, [showcaseInView, showcasePaused, prefersReducedMotion]);

  useEffect(() => {
    const el = showcaseRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) el.classList.add('is-visible');
        setShowcaseInView(entry.isIntersecting);
      },
      { threshold: 0.2 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleShowcaseJump = useCallback((i) => {
    setShowcaseActiveIndex(i);
  }, []);

  const handleShowcaseKeyNav = useCallback((event, index, refs) => {
    const max = SHOWCASE_CARDS.length - 1;
    let nextIndex = null;
    if (event.key === 'ArrowRight') nextIndex = index === max ? 0 : index + 1;
    if (event.key === 'ArrowLeft') nextIndex = index === 0 ? max : index - 1;
    if (event.key === 'Home') nextIndex = 0;
    if (event.key === 'End') nextIndex = max;
    if (nextIndex === null) return;
    event.preventDefault();
    setShowcaseActiveIndex(nextIndex);
    refs.current[nextIndex]?.focus();
  }, []);

  const closeOnboarding = useCallback(() => {
    setOnboardingOpen(false);
    try {
      localStorage.setItem(LANDING_ONBOARDING_KEY, '1');
    } catch {}
  }, []);

  const handleIdeFocusCapture = useCallback(() => setShowcasePaused(true), []);
  const handleIdeBlurCapture = useCallback((e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) setShowcasePaused(false);
  }, []);
  const handleIdePointerEnter = useCallback(() => setShowcasePaused(true), []);
  const handleIdePointerLeave = useCallback(() => setShowcasePaused(false), []);

  const activeCard = SHOWCASE_CARDS[showcaseActiveIndex];
  const activeColor = TRACK_META[activeCard.topic]?.color ?? 'var(--accent)';
  const activeCodeLineCount = useMemo(
    () => activeCard.solutionCode.split('\n').length,
    [activeCard]
  );
  const highlightedLines = useMemo(
    () => highlightCode(activeCard.solutionCode, activeCard.language),
    [activeCard]
  );

  const trackTabs = useMemo(
    () =>
      TOPICS.map((topic) => {
        const meta = TRACK_META[topic];
        const trackData = dashData?.tracks?.[topic];
        const solved = trackData?.solved ?? 0;
        const total = trackData?.total ?? meta.totalQuestions;
        const completion = total > 0 ? Math.round((solved / total) * 100) : 0;

        return {
          id: topic,
          label: meta.label,
          description: meta.description,
          color: meta.color,
          solved,
          total,
          completion,
          difficulties: TRACK_DIFFICULTIES[topic],
          samples: SAMPLE_TIERS[topic],
        };
      }),
    [dashData]
  );

  function handleTabChange(tabId) {
    localStorage.setItem('landingActiveTab', tabId);
    startTransition(() => setActiveTab(tabId));
  }

  return (
    <>
      <Topbar showPricingLink={!user} />

      <main className="landing-page">
        {user ? (
          <LoggedInWelcome user={user} dashData={dashData} />
        ) : (
          <section className="landing-hero">
            <div className="landing-hero-inner">
              <span className="landing-kicker">SQL · Python · PySpark · pandas</span>
              <h1 className="landing-title">Get sharp at data interviews.</h1>
              <p className="landing-copy">
                Four focused tracks covering query fluency, coding fundamentals, dataframe work, and Spark judgment.
                Practice in a calm workspace with instant feedback and guided progression.
              </p>
              <div className="landing-actions">
                <a className="btn btn-primary" href="#landing-tracks">Explore tracks ↓</a>
                <Link className="btn btn-secondary" to="/auth">Create account</Link>
              </div>
            </div>
          </section>
        )}

        {!user && (
          <>
            <div className="landing-proof-row" aria-label="Platform stats">
              <span className="landing-proof-stat"><strong>350</strong> questions</span>
              <span className="landing-proof-sep" aria-hidden="true" />
              <span className="landing-proof-stat"><strong>4</strong> tracks</span>
              <span className="landing-proof-sep" aria-hidden="true" />
              <span className="landing-proof-stat"><strong>11</strong> real-world datasets</span>
              <span className="landing-proof-sep" aria-hidden="true" />
              <span className="landing-proof-stat">instant feedback</span>
            </div>

            <section className="landing-showcase">
              <div className="landing-showcase-inner" ref={showcaseRef}>
                <div className="landing-showcase-header">
                  <h2 className="landing-showcase-title">See what you&rsquo;ll be solving.</h2>
                  <p className="landing-showcase-subtitle">
                    Read the problem. Study the solution. Build the intuition you&rsquo;ll draw on in the room.
                  </p>
                </div>

            <div
              className="landing-ide"
              style={{ '--active-color': activeColor }}
              onMouseEnter={handleIdePointerEnter}
              onMouseLeave={handleIdePointerLeave}
              onFocusCapture={handleIdeFocusCapture}
              onBlurCapture={handleIdeBlurCapture}
            >
              <div className="landing-ide-chrome">
                <span className="ide-traffic" aria-hidden="true">
                  <i /><i /><i />
                </span>
                <div className="ide-tabs" role="tablist" aria-label="Track preview">
                  {SHOWCASE_CARDS.map((card, i) => {
                    const isActive = i === showcaseActiveIndex;
                    const tabColor = TRACK_META[card.topic]?.color ?? 'var(--accent)';
                    return (
                      <button
                        key={card.topic}
                        type="button"
                        role="tab"
                        aria-selected={isActive}
                        aria-controls="ide-body"
                        tabIndex={0}
                        className={`ide-tab${isActive ? ' is-active' : ''}`}
                        style={{ '--tab-color': tabColor }}
                        onClick={() => handleShowcaseJump(i)}
                        onKeyDown={(event) => handleShowcaseKeyNav(event, i, showcaseTabRefs)}
                        ref={(el) => { showcaseTabRefs.current[i] = el; }}
                      >
                        <span className="ide-tab-dot" aria-hidden="true" />
                        <span className="ide-tab-filename">{card.fileName}</span>
                      </button>
                    );
                  })}
                </div>
                <span className={`ide-difficulty-pill ide-difficulty-${activeCard.difficulty}`}>
                  {activeCard.difficulty}
                </span>
              </div>

              <div className="landing-ide-body" id="ide-body" role="tabpanel">
                <div key={activeCard.topic} className="ide-body-inner">
                  <div className="ide-brief">
                    <span className="ide-brief-kicker">Problem</span>
                    <h3 className="ide-brief-title">{activeCard.title}</h3>
                    <div className="ide-brief-meta">
                      <span className="ide-brief-meta-dot" style={{ background: activeColor }} />
                      <span>{TRACK_META[activeCard.topic]?.label}</span>
                      <span aria-hidden="true">·</span>
                      <span>{activeCard.difficulty}</span>
                    </div>
                    <p className="ide-brief-para">{activeCard.briefParagraph}</p>
                    {activeCard.returnsNote && (
                      <p className="ide-brief-returns">{activeCard.returnsNote}</p>
                    )}
                    <div className="ide-brief-concepts">
                      <span className="ide-brief-concepts-label">Concepts</span>
                      <span className="ide-brief-concepts-value">
                        {activeCard.concepts.join(' · ')}
                      </span>
                    </div>
                  </div>

                  <div className="ide-code-pane" aria-label={`${activeCard.fileName} solution`}>
                    <div className="ide-code-filename" aria-hidden="true">
                      <span className="ide-code-filename-dot" style={{ background: activeColor }} />
                      {activeCard.fileName}
                    </div>
                    <pre className="ide-code-block">
                      <span className="ide-code-gutter" aria-hidden="true">
                        {Array.from({ length: activeCodeLineCount }, (_, n) => (
                          <span key={n}>{n + 1}</span>
                        ))}
                      </span>
                      <code className={`ide-code ide-code--${activeCard.language}`}>
                        {highlightedLines}
                      </code>
                    </pre>
                  </div>
                </div>
              </div>

              <div className="landing-ide-statusbar">
                <div className="ide-statusbar-meta">
                  <span className="ide-statusbar-lang">{activeCard.language.toUpperCase()}</span>
                  <span aria-hidden="true" className="ide-statusbar-sep">·</span>
                  <span className="ide-statusbar-lines">{activeCodeLineCount} lines</span>
                </div>
                <div className="ide-statusbar-dots" role="tablist" aria-label="Jump to track">
                  {SHOWCASE_CARDS.map((card, i) => {
                    const isActive = i === showcaseActiveIndex;
                    const dotColor = TRACK_META[card.topic]?.color ?? 'var(--accent)';
                    return (
                      <button
                        key={card.topic}
                        type="button"
                        role="tab"
                        aria-selected={isActive}
                        aria-label={`Show ${TRACK_META[card.topic]?.label}`}
                        tabIndex={0}
                        className={`ide-rotation-dot${isActive ? ' is-active' : ''}`}
                        style={{ '--dot-color': dotColor }}
                        onClick={() => handleShowcaseJump(i)}
                        onKeyDown={(event) => handleShowcaseKeyNav(event, i, showcaseDotRefs)}
                        ref={(el) => { showcaseDotRefs.current[i] = el; }}
                      />
                    );
                  })}
                </div>
              </div>
            </div>
              </div>
            </section>

            <section className="landing-companies">
              <div className="landing-section-inner">
                <p className="landing-companies-label">Practice questions from top companies:</p>
                <div className="landing-companies-row">
                  {['Meta', 'Google', 'Amazon', 'Stripe', 'Airbnb', 'Netflix', 'Uber', 'Microsoft', 'LinkedIn', 'Shopify'].map((company) => (
                    <span key={company} className="landing-company-chip">
                      {company}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          </>
        )}

        <section className="landing-practice-section" id="landing-tracks">
          <div className="landing-practice-heading">
            <h2 className="landing-practice-title">Practice tracks</h2>
            <p className="landing-practice-copy">
              Four focused tracks — from query fluency to distributed systems. Each with a structured challenge bank and free samples to explore first.
            </p>
          </div>

          <div className="track-cards-grid">
            {trackTabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  className={`track-card${isActive ? ' is-active' : ''}`}
                  style={{ '--track-color': tab.color }}
                  onClick={() => handleTabChange(tab.id)}
                  aria-pressed={isActive}
                  aria-label={`Select ${tab.label} track`}
                >
                  <div className="track-card-header">
                    <span className="track-card-dot" />
                    <span className="track-card-name">{tab.label}</span>
                    <span className="track-card-count">{tab.total} Q</span>
                  </div>
                  <p className="track-card-desc">{tab.description}</p>
                  <div className="track-card-difficulties">
                    <span className="track-diff-chip track-diff-chip--easy">{tab.difficulties.easy} easy</span>
                    <span className="track-diff-chip track-diff-chip--medium">{tab.difficulties.medium} medium</span>
                    <span className="track-diff-chip track-diff-chip--hard">{tab.difficulties.hard} hard</span>
                  </div>
                  {user && (
                    <div className="track-card-progress">
                      <TrackProgressBar solved={tab.solved} total={tab.total} color={tab.color} showLabel={false} />
                      <span className="track-card-progress-label">
                        {tab.solved > 0 ? `${tab.solved} of ${tab.total} solved` : `Not started`}
                      </span>
                    </div>
                  )}
                  <div className="track-card-footer">
                    <span className="track-card-cta">
                      {tab.solved > 0 ? 'Continue' : 'Start track'} →
                    </span>
                    {isActive && <span className="track-card-active-label">▼ samples below</span>}
                  </div>
                </button>
              );
            })}
          </div>

          {trackTabs.map((tab) => {
            if (activeTab !== tab.id) return null;
            const hasStarted = tab.solved > 0;
            return (
              <div key={tab.id} className="track-samples-strip" style={{ '--track-color': tab.color }}>
                <div className="track-samples-header">
                  <div className="track-samples-header-text">
                    <h3 className="track-samples-title">
                      <span className="track-samples-dot" />
                      Free samples — {tab.label}
                    </h3>
                    <p className="track-samples-desc">
                      3 questions per difficulty tier. No account required and no progress recorded.
                    </p>
                  </div>
                  <div className="track-samples-actions">
                    <Link
                      className="btn btn-primary"
                      to={`/practice/${tab.id}`}
                      style={{ background: tab.color, borderColor: tab.color }}
                    >
                      {hasStarted ? 'Continue track' : 'Open full track'} →
                    </Link>
                    {!user && (
                      <Link className="btn btn-secondary" to="/auth">Create account</Link>
                    )}
                  </div>
                </div>
                <div className="landing-samples-grid">
                  {tab.samples.map(({ difficulty, title, copy }) => (
                    <Link
                      key={difficulty}
                      className="sample-tile"
                      to={`/sample/${tab.id}/${difficulty}`}
                      style={{ '--tile-color': tab.color }}
                    >
                      <span className={`badge badge-${difficulty}`}>{difficulty}</span>
                      <strong className="sample-tile-title">{title}</strong>
                      <p>{copy}</p>
                      <span className="sample-tile-footer">Start sample →</span>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </section>

        {displayedPaths.length > 0 && (
          <section className="landing-paths">
            <div className="landing-section-inner">
              <div className="landing-paths-header">
                <div>
                  <h2 className="landing-paths-title">Structured learning paths</h2>
                  <p className="landing-paths-sub">Curated sequences from basics to advanced.</p>
                </div>
                <button className="landing-paths-shuffle" onClick={shufflePaths} title="Shuffle paths" aria-label="Shuffle learning paths">
                  ⇄ Shuffle
                </button>
              </div>
              <div className="landing-paths-grid">
                {displayedPaths.map(p => (
                  <PathProgressCard key={p.slug} path={p} />
                ))}
              </div>
            </div>
          </section>
        )}

        {/* Tier comparison */}
        {userPlan !== 'lifetime_elite' && (
        <section id="landing-pricing" className="landing-tier-section">
          <div className="landing-tier-inner">
            <h2 className="landing-tier-title">Simple pricing</h2>
            <div className="landing-tier-grid">

              {/* ── Free ── */}
              <div className="landing-tier-col">
                <div className="landing-tier-col-header">
                  <span className="landing-tier-name">Free</span>
                  <div className="landing-tier-price">
                    <span className="landing-tier-price-amount">₹0</span>
                  </div>
                </div>
                <ul className="landing-tier-list">
                  <li>{TOTAL_EASY} easy questions (32 SQL · 30 Python · 29 Pandas · 38 PySpark)</li>
                  <li>Unlock medium + hard as you solve (batch-gated)</li>
                  <li>1 mock interview per day</li>
                  <li>2 learning paths per track</li>
                </ul>
                <div className="landing-tier-cta">
                  {userPlan === 'free' && (
                    <span className="landing-tier-current">Current plan</span>
                  )}
                </div>
              </div>

              {/* ── Pro ── */}
              <div className="landing-tier-col landing-tier-col--featured">
                <div className="landing-tier-col-header">
                  <span className="landing-tier-badge">Most popular</span>
                  <span className="landing-tier-name">Pro</span>
                  <div className="landing-tier-price">
                    <span className="landing-tier-price-amount">₹799</span>
                    <span className="landing-tier-price-period">/mo</span>
                  </div>
                </div>
                <ul className="landing-tier-list">
                  <li>Everything in Free</li>
                  <li>All {TOTAL_QUESTIONS} questions — every medium + hard</li>
                  <li>All learning paths</li>
                  <li>3 mock interviews per day (up to hard)</li>
                </ul>
                <div className="landing-tier-cta">
                  {proColCta() === 'current' && (
                    <span className="landing-tier-current">Current plan</span>
                  )}
                  {proColCta() === 'both' && (
                    <UpgradeButton tier="pro" source="landing_tier" />
                  )}
                  {(proColCta() === 'both' || proColCta() === 'lifetime_only') && (
                    <UpgradeButton
                      tier="lifetime_pro"
                      label={proColCta() === 'lifetime_only' ? 'Switch to lifetime — ₹7,999' : 'Lifetime access — ₹7,999'}
                      compact
                      className="landing-tier-lifetime-btn"
                      source="landing_tier_lifetime"
                    />
                  )}
                </div>
              </div>

              {/* ── Elite ── */}
              <div className="landing-tier-col">
                <div className="landing-tier-col-header">
                  <span className="landing-tier-name">Elite</span>
                  <div className="landing-tier-price">
                    <span className="landing-tier-price-amount">₹1,599</span>
                    <span className="landing-tier-price-period">/mo</span>
                  </div>
                </div>
                <ul className="landing-tier-list">
                  <li>Everything in Pro</li>
                  <li>Company filter — Meta, Google, Stripe, Airbnb…</li>
                  <li>Unlimited daily mock interviews</li>
                  <li>Weak-spot insights after every session</li>
                </ul>
                <div className="landing-tier-cta">
                  {eliteColCta() === 'current' && (
                    <span className="landing-tier-current">Current plan</span>
                  )}
                  {eliteColCta() === 'both' && (
                    <UpgradeButton tier="elite" source="landing_tier" />
                  )}
                  {(eliteColCta() === 'both' || eliteColCta() === 'lifetime_only') && (
                    <UpgradeButton
                      tier="lifetime_elite"
                      label={eliteColCta() === 'lifetime_only' ? 'Switch to lifetime — ₹14,999' : 'Lifetime access — ₹14,999'}
                      compact
                      className="landing-tier-lifetime-btn"
                      source="landing_tier_lifetime"
                    />
                  )}
                </div>
              </div>

            </div>
          </div>
        </section>
        )}

        <OnboardingTooltip
          isOpen={onboardingOpen}
          onClose={closeOnboarding}
          steps={[
            {
              targetSelector: '.track-cards-grid',
              title: 'Pick your track',
              body: 'SQL, Python, Pandas, or PySpark — each has its own question bank with easy, medium, and hard tiers. Start with whichever matches your next interview.',
            },
            {
              targetSelector: '.track-samples-strip',
              title: 'Warm up with free samples',
              body: 'Every track has 3 free sample questions per difficulty. No account needed — just open one and start writing.',
            },
            {
              targetSelector: '.landing-paths',
              title: 'Follow a learning path',
              body: 'Paths are curated question sequences that build skill progressively. Completing a starter path also fast-tracks your unlock progress.',
            },
            {
              targetSelector: '#landing-pricing',
              title: 'Free to start, easy to upgrade',
              body: 'All easy questions are free — no card required. Upgrade to Pro or Elite when you want full access to medium and hard questions.',
            },
          ]}
        />
      </main>
    </>
  );
}
