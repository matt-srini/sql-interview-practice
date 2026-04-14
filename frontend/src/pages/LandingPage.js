import { startTransition, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import TrackProgressBar from '../components/TrackProgressBar';
import PathProgressCard from '../components/PathProgressCard';
import Topbar from '../components/Topbar';
import { useTheme } from '../App';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

const TRACK_DIFFICULTIES = {
  sql:           { easy: 30, medium: 30, hard: 26 },
  python:        { easy: 30, medium: 25, hard: 20 },
  'python-data': { easy: 30, medium: 25, hard: 20 },
  pyspark:       { easy: 30, medium: 25, hard: 20 },
};

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
    label: 'SQL',
    color: '#5B6AF0',
    difficulty: 'medium',
    title: '7-Day Rolling Revenue',
    questionText: `-- Challenge: For each day, compute the sum
-- of order revenue over the past 7 days
-- (including today). Return: order_date,
-- daily_revenue, rolling_7d_revenue.`,
    answerCode: `SELECT
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
    label: 'Python',
    color: '#2D9E6B',
    difficulty: 'hard',
    title: 'Coin Change (DP)',
    questionText: `# Challenge: Given coin denominations and
# an amount, return the minimum number of
# coins needed. Return -1 if impossible.
# Time: O(amount × coins). Space: O(amount).`,
    answerCode: `def solve(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for x in range(coin, amount + 1):
            dp[x] = min(dp[x],
                        dp[x - coin] + 1)
    return (dp[amount]
            if dp[amount] != float('inf')
            else -1)`,
  },
  {
    label: 'Pandas',
    color: '#C47F17',
    difficulty: 'medium',
    title: 'User Avg Order (Transform)',
    questionText: `# Challenge: Add a column showing each
# user's average order value on every row.
# Use groupby + transform so the result
# aligns with the original DataFrame index.`,
    answerCode: `def solve(df_orders):
    df = df_orders.copy()
    df['user_avg_order'] = (
        df.groupby('user_id')['net_amount']
          .transform('mean')
          .round(2)
    )
    return df[['order_id', 'user_id',
               'net_amount',
               'user_avg_order']]`,
  },
  {
    label: 'PySpark',
    color: '#D94F3D',
    difficulty: 'medium',
    title: 'repartition vs coalesce',
    questionText: `# Challenge: You need to reduce a DataFrame
# from 200 partitions to 10 for writing.
# Which operation avoids a full shuffle,
# and when does that matter?`,
    answerCode: `# coalesce(10) — merges partitions locally,
# no full shuffle. Best when REDUCING count.
#
# repartition(10) — full shuffle, even
# distribution. Use when INCREASING or when
# data is skewed across partitions.
#
# → For reducing: coalesce saves significant
#   network I/O and shuffle overhead.
df = df.coalesce(10)`,
  },
];

export default function LandingPage() {
  const { user, logout } = useAuth();
  const { theme, setTheme, resolvedTheme } = useTheme();

  function cycleTheme() {
    const next = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    setTheme(next);
  }
  const themeIcon = theme === 'system' ? '◐' : resolvedTheme === 'dark' ? '☀' : '☾';
  const themeLabel = theme === 'system' ? 'Theme: system' : theme === 'light' ? 'Theme: light' : 'Theme: dark';
  const [dashData, setDashData] = useState(null);
  const [activeTab, setActiveTab] = useState(
    () => sessionStorage.getItem('landingActiveTab') || 'sql'
  );

  const showcaseRef = useRef(null);
  const [showcaseActiveIndex, setShowcaseActiveIndex] = useState(0);
  const [showcaseDisplayed, setShowcaseDisplayed] = useState('');
  const [showcasePhase, setShowcasePhase] = useState('question');
  const showcaseTimers = useRef({ interval: null, timeout: null });

  const [paths, setPaths] = useState([]);
  const [displayedPaths, setDisplayedPaths] = useState([]);

  function pickRandom(arr, n) {
    const shuffled = [...arr].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, n);
  }

  const shufflePaths = () => setDisplayedPaths(pickRandom(paths, 4));

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

  useEffect(() => {
    const card = SHOWCASE_CARDS[showcaseActiveIndex];
    const timers = showcaseTimers.current;

    if (timers.interval) clearInterval(timers.interval);
    if (timers.timeout) clearTimeout(timers.timeout);

    setShowcaseDisplayed('');
    setShowcasePhase('question');

    let i = 0;
    const question = card.questionText;

    timers.interval = setInterval(() => {
      i++;
      setShowcaseDisplayed(question.slice(0, i));
      if (i >= question.length) {
        clearInterval(timers.interval);
        timers.timeout = setTimeout(() => {
          setShowcasePhase('answer');
          let j = 0;
          const answer = card.answerCode;
          const fullText = question + '\n\n' + answer;
          const startLen = question.length + 2;
          timers.interval = setInterval(() => {
            j++;
            setShowcaseDisplayed(fullText.slice(0, startLen + j));
            if (j >= answer.length) {
              clearInterval(timers.interval);
              timers.timeout = setTimeout(() => {
                setShowcaseActiveIndex(prev => (prev + 1) % SHOWCASE_CARDS.length);
              }, 1500);
            }
          }, 10);
        }, 800);
      }
    }, 12);

    return () => {
      if (timers.interval) clearInterval(timers.interval);
      if (timers.timeout) clearTimeout(timers.timeout);
    };
  }, [showcaseActiveIndex]);

  useEffect(() => {
    const el = showcaseRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) el.classList.add('is-visible'); },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

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
    sessionStorage.setItem('landingActiveTab', tabId);
    startTransition(() => setActiveTab(tabId));
  }

  return (
    <>
      <Topbar />

      <main className="landing-page">
        {!user && (
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

        <section className="landing-showcase">
          <div className="landing-showcase-inner" ref={showcaseRef}>
            <div className="landing-showcase-header">
              <span className="landing-showcase-eyebrow">All four tracks. Real interview problems.</span>
              <h2 className="landing-showcase-title">See what you&rsquo;ll be solving.</h2>
            </div>

            <div className="landing-showcase-grid">
              {SHOWCASE_CARDS.map((card, i) => (
                <div
                  key={card.label}
                  className={`showcase-card${showcaseActiveIndex === i ? ' is-active' : ''}`}
                  style={showcaseActiveIndex === i ? { '--active-color': card.color } : {}}
                >
                  <div className="showcase-card-header">
                    <span className="showcase-track-dot" style={{ background: card.color }} />
                    <span className="showcase-track-label">{card.label}</span>
                    <span className="showcase-difficulty-badge">{card.difficulty}</span>
                  </div>
                  <div className="showcase-question-title">{card.title}</div>
                  <div className="showcase-phase-label">
                    {showcaseActiveIndex === i ? (showcasePhase === 'question' ? 'Question' : 'Answer') : ''}
                  </div>
                  <pre className="showcase-code-block">
                    <code>{showcaseActiveIndex === i ? showcaseDisplayed : ''}</code>
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-companies">
          <div className="container">
            <p className="landing-companies-label">Practice questions from top companies:</p>
            <div className="landing-companies-row">
              {['Meta', 'Google', 'Amazon', 'Stripe', 'Airbnb', 'Netflix', 'Uber', 'Microsoft', 'LinkedIn', 'Shopify'].map((company) => (
                <a
                  key={company}
                  className="landing-company-chip"
                  href="#landing-tracks"
                >
                  {company}
                </a>
              ))}
            </div>
          </div>
        </section>

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
                      3 questions per difficulty tier. No account required, no progress recorded.
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
            <div className="container">
              <div className="landing-paths-header">
                <div>
                  <h2 className="landing-paths-title">Structured learning paths</h2>
                  <p className="landing-paths-sub">Curated sequences from basics to advanced.</p>
                </div>
                <button className="landing-paths-shuffle" onClick={shufflePaths} title="Shuffle paths">
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
        <section className="landing-tier-section">
          <div className="landing-tier-inner">
            <h2 className="landing-tier-title">What's included</h2>
            <div className="landing-tier-grid">
              <div className="landing-tier-col">
                <div className="landing-tier-col-header">
                  <span className="landing-tier-name">Free</span>
                </div>
                <ul className="landing-tier-list">
                  <li>All easy questions</li>
                  <li>Unlock medium + hard via curated paths or solo practice</li>
                  <li>Easy mock interviews</li>
                  <li>2 free learning paths per track</li>
                </ul>
              </div>
              <div className="landing-tier-col landing-tier-col--featured">
                <div className="landing-tier-col-header">
                  <span className="landing-tier-name">Pro</span>
                </div>
                <ul className="landing-tier-list">
                  <li>Everything in Free</li>
                  <li>All medium + hard across all tracks</li>
                  <li>All learning paths</li>
                  <li>Daily hard mock interviews</li>
                </ul>
              </div>
              <div className="landing-tier-col">
                <div className="landing-tier-col-header">
                  <span className="landing-tier-name">Elite</span>
                </div>
                <ul className="landing-tier-list">
                  <li>Everything in Pro</li>
                  <li>Company-filtered mock interviews</li>
                  <li>Weak-spot insights after every session</li>
                  <li>Harder interview-realistic mock questions</li>
                </ul>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
