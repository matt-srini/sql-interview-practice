import { Fragment, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Topbar from '../components/Topbar';
import UpgradeButton from '../components/UpgradeButton';
import { useAuth } from '../contexts/AuthContext';
import { detectCurrency } from '../utils/currency';
import { COMPARISON_TIERS, COMPARISON_GROUPS, FREE_UNLOCK } from '../data/tierFeatures';

const PAID_PLANS = ['pro', 'elite', 'lifetime_pro', 'lifetime_elite'];

function TierValue({ value }) {
  if (value === true)  return <span className="pricing-cell-check" aria-label="Included">✓</span>;
  if (value === false) return <span className="pricing-cell-dash" aria-label="Not included">—</span>;
  return <span className="pricing-cell-value">{value}</span>;
}

function UnlockLadder({ steps }) {
  return (
    <ol className="pricing-unlock-ladder">
      {steps.map(([from, to], i) => (
        <li key={i} className="pricing-unlock-step">
          <span className="pricing-unlock-from">{from}</span>
          <span className="pricing-unlock-arrow" aria-hidden="true">→</span>
          <span className="pricing-unlock-to">{to}</span>
        </li>
      ))}
    </ol>
  );
}

export default function PricingPage() {
  const { user } = useAuth();
  const userPlan = user?.plan ?? 'free';
  const isPaid = PAID_PLANS.includes(userPlan);
  const currency = detectCurrency();

  useEffect(() => { window.scrollTo(0, 0); }, []);

  // Column order mirrors COMPARISON_TIERS (free / pro / elite)
  const tierIds = COMPARISON_TIERS.map(t => t.id);

  return (
    <div className="pricing-page">
      <Helmet>
        <title>Plans &amp; feature comparison — datathink</title>
        <meta name="description" content="Compare datathink Free, Pro and Elite — every feature spelled out, plus how Free unlocks medium and hard questions." />
        <meta property="og:title" content="Plans & feature comparison — datathink" />
        <meta property="og:description" content="Compare datathink Free, Pro and Elite — every feature spelled out, plus how Free unlocks medium and hard questions." />
        <meta property="og:image" content="https://datathink.co/og-image.png?v=4" />
        <meta property="og:url" content="https://datathink.co/pricing" />
        <meta name="twitter:card" content="summary_large_image" />
        <link rel="canonical" href="https://datathink.co/pricing" />
      </Helmet>

      <Topbar />

      <main className="pricing-main">
        {/* ── Header ───────────────────────────────────────────── */}
        <header className="pricing-header">
          <div className="pricing-inner">
            <p className="pricing-eyebrow">PLANS</p>
            <h1 className="pricing-h1">Every feature, spelled out.</h1>
            <p className="pricing-sub">
              No vague tiers — here's exactly what each plan gives you, and how far Free actually gets you.
            </p>
          </div>
        </header>

        {/* ── Tier summary cards ───────────────────────────────── */}
        <section className="pricing-section pricing-tier-summary" aria-label="Plan overview">
          <div className="pricing-inner">
            <div className="pricing-tier-cards">
              {COMPARISON_TIERS.map(tier => (
                <div
                  key={tier.id}
                  className={`pricing-tier-card${tier.featured ? ' pricing-tier-card--featured' : ''}`}
                >
                  <div className="pricing-tier-card-name">{tier.name}</div>
                  <p className="pricing-tier-card-blurb">{tier.blurb}</p>
                  <div className="pricing-tier-card-cta">
                    {tier.id === 'free' ? (
                      <span className="pricing-free-badge">Free forever</span>
                    ) : tier.id === 'pro' ? (
                      userPlan !== 'pro' && userPlan !== 'lifetime_pro' && userPlan !== 'lifetime_elite' && userPlan !== 'elite' ? (
                        <UpgradeButton
                          tier="pro"
                          source="pricing_page"
                          currency={currency}
                          successPath="/pricing?upgraded=true"
                        />
                      ) : null
                    ) : (
                      userPlan !== 'elite' && userPlan !== 'lifetime_elite' ? (
                        <UpgradeButton
                          tier="elite"
                          source="pricing_page"
                          currency={currency}
                          successPath="/pricing?upgraded=true"
                        />
                      ) : null
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Feature comparison table ─────────────────────────── */}
        <section className="pricing-section" aria-label="Feature comparison">
          <div className="pricing-inner">
            <div className="pricing-table-scroll">
              <table className="pricing-table">
                <thead>
                  <tr>
                    <th className="pricing-th-feature" scope="col">Feature</th>
                    {COMPARISON_TIERS.map(t => (
                      <th
                        key={t.id}
                        scope="col"
                        className={`pricing-th-tier${t.featured ? ' pricing-th-tier--featured' : ''}`}
                      >
                        {t.name}
                        {t.featured && <span className="pricing-th-badge">Most popular</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {COMPARISON_GROUPS.map(group => (
                    <Fragment key={group.group}>
                      {/* Group header row */}
                      <tr className="pricing-group-row">
                        <td colSpan={1 + tierIds.length} className="pricing-group-label">
                          {group.group}
                        </td>
                      </tr>
                      {/* Feature rows */}
                      {group.rows.map((row, ri) => (
                        <tr
                          key={`${group.group}-${ri}`}
                          className={`pricing-feature-row${ri % 2 === 1 ? ' pricing-feature-row--alt' : ''}`}
                        >
                          <td className="pricing-td-feature">
                            <span className="pricing-feature-name">{row.feature}</span>
                            {row.blurb && (
                              <span className="pricing-feature-blurb">{row.blurb}</span>
                            )}
                          </td>
                          {tierIds.map(tid => (
                            <td
                              key={tid}
                              className={`pricing-td-value${COMPARISON_TIERS.find(t => t.id === tid)?.featured ? ' pricing-td-value--featured' : ''}`}
                            >
                              <TierValue value={row[tid]} />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ── Free unlock ladders ──────────────────────────────── */}
        <section className="pricing-section pricing-unlock-section" aria-label="Free tier unlock ladders">
          <div className="pricing-inner">
            <h2 className="pricing-section-h2">How Free unlocks questions</h2>
            <p className="pricing-unlock-intro">{FREE_UNLOCK.intro}</p>
            <div className="pricing-unlock-grid">
              {FREE_UNLOCK.groups.map(group => (
                <div key={group.label} className="pricing-unlock-card">
                  <div className="pricing-unlock-card-header">
                    <span className="pricing-unlock-label">{group.label}</span>
                    <span className="pricing-unlock-tracks">{group.tracks}</span>
                  </div>
                  <div className="pricing-unlock-difficulty">
                    <p className="pricing-unlock-diff-heading">Medium</p>
                    <UnlockLadder steps={group.medium} />
                  </div>
                  <div className="pricing-unlock-difficulty">
                    <p className="pricing-unlock-diff-heading">Hard</p>
                    <UnlockLadder steps={group.hard} />
                  </div>
                  <p className="pricing-unlock-cap">{group.cap}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Closing CTA ──────────────────────────────────────── */}
        <section className="pricing-section pricing-closing-cta" aria-label="Get started">
          <div className="pricing-inner pricing-closing-cta-inner">
            {!isPaid && (
              <>
                <UpgradeButton
                  tier="pro"
                  source="pricing_page_closing"
                  currency={currency}
                  successPath="/pricing?upgraded=true"
                />
                <UpgradeButton
                  tier="elite"
                  source="pricing_page_closing"
                  currency={currency}
                  successPath="/pricing?upgraded=true"
                />
              </>
            )}
            <Link to="/sample" className="pricing-start-free-link">
              Try a free sample first →
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
