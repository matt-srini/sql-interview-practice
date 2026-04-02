import { startTransition, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import { TRACK_META } from '../contexts/TopicContext';
import TrackProgressBar from '../components/TrackProgressBar';

const TOPICS = ['sql', 'python', 'python-data', 'pyspark'];

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
  const [dashData, setDashData] = useState(null);
  const [activeTab, setActiveTab] = useState('sql');

  const showcaseRef = useRef(null);
  const [showcaseActiveIndex, setShowcaseActiveIndex] = useState(0);
  const [showcaseDisplayed, setShowcaseDisplayed] = useState('');
  const [showcasePhase, setShowcasePhase] = useState('question');
  const showcaseTimers = useRef({ interval: null, timeout: null });

  useEffect(() => {
    if (user) {
      api.get('/dashboard').then((res) => setDashData(res.data)).catch(() => {});
      return;
    }
    setDashData(null);
  }, [user]);

  // Scroll to hash on mount (e.g. /#landing-tracks from back arrow)
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash) return;
    const el = document.getElementById(hash.slice(1));
    if (el) {
      // Small delay to let the page render first
      setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 80);
    }
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
          samples: SAMPLE_TIERS[topic],
        };
      }),
    [dashData]
  );

  function handleTabChange(tabId) {
    startTransition(() => setActiveTab(tabId));
  }

  return (
    <>
      <header className="topbar landing-topbar">
        <div className="container topbar-inner landing-topbar-inner">
          <div className="landing-topbar-left">
            <Link className="landing-brand brand-wordmark" to="/">datanest</Link>
          </div>
          <div className="landing-topbar-right">
            <Link className="topbar-auth-link" to="/dashboard">Dashboard</Link>
            {user ? (
              <div className="topbar-user-pill">
                <span className="topbar-user-name">{user.name || user.email}</span>
                <button type="button" className="topbar-signout-btn" onClick={logout}>
                  Sign out
                </button>
              </div>
            ) : (
              <Link className="topbar-auth-link" to="/auth">Login</Link>
            )}
          </div>
        </div>
      </header>

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

        <section className="landing-practice-section" id="landing-tracks">
          <div className="landing-practice-heading">
            <h2 className="landing-practice-title">Practice by track</h2>
            <p className="landing-practice-copy">
              Pick a lane, skim the sample rounds, and jump into the challenge flow when you&rsquo;re ready.
            </p>
          </div>

          <div className="landing-track-nav landing-track-nav--practice" role="tablist" aria-label="Track tabs">
            {trackTabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  aria-controls={`landing-tab-panel-${tab.id}`}
                  id={`landing-tab-${tab.id}`}
                  className={`landing-track-pill${isActive ? ' is-active' : ''}`}
                  style={{ '--pill-color': tab.color }}
                  onClick={() => handleTabChange(tab.id)}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          <div className="landing-tab-panels">
            {trackTabs.map((tab) => {
              const isActive = activeTab === tab.id;
              const hasStarted = tab.solved > 0;
              const progressLabel = user
                ? `${tab.completion}% complete`
                : `${tab.total} challenge questions`;

              return (
                <section
                  key={tab.id}
                  id={`landing-tab-panel-${tab.id}`}
                  role="tabpanel"
                  aria-labelledby={`landing-tab-${tab.id}`}
                  hidden={!isActive}
                  className={`landing-tab-panel${isActive ? ' is-active' : ''}`}
                >
                  <div className="landing-panel-header">
                    <div>
                      <h3>{tab.label}</h3>
                      <p>{tab.description}</p>
                    </div>
                    <span className="landing-panel-tag" style={{ borderColor: tab.color, color: tab.color }}>
                      {progressLabel}
                    </span>
                  </div>

                  <div className="landing-panel-body">
                    <div className="landing-panel-progress">
                      <TrackProgressBar solved={tab.solved} total={tab.total} color={tab.color} showLabel={false} />
                      <span className="landing-panel-progress-copy">
                        {user
                          ? `${tab.solved} solved out of ${tab.total}`
                          : 'Sign in to save progress and carry it across devices'}
                      </span>
                    </div>
                    <div className="landing-panel-actions">
                      <Link className="btn btn-primary" to={`/practice/${tab.id}`}>
                        {hasStarted ? 'Continue track' : 'Start track'} →
                      </Link>
                      {!user && <Link className="btn btn-secondary" to="/auth">Create account</Link>}
                    </div>
                  </div>

                  <div className="landing-panel-samples">
                    <div className="landing-panel-samples-header">
                      <div>
                        <h4>Sample rounds</h4>
                        <p>Try an easy, medium, or hard slice without affecting challenge progress.</p>
                      </div>
                      <span className="landing-panel-tag">No progress recorded</span>
                    </div>

                    <div className="landing-samples-grid">
                      {tab.samples.map(({ difficulty, title, copy }) => (
                        <Link key={difficulty} className="sample-tile" to={`/sample/${tab.id}/${difficulty}`}>
                          <span className={`badge badge-${difficulty}`}>{difficulty}</span>
                          <strong className="sample-tile-title">{title}</strong>
                          <p>{copy}</p>
                          <span className="sample-tile-footer">Open sample →</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                </section>
              );
            })}
          </div>
        </section>
      </main>
    </>
  );
}
