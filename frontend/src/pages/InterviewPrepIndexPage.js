import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import Topbar from '../components/Topbar';
import { Reveal } from '../components/Reveal';
import { ROLES } from '../roleRegistry';
import { TRACK_META } from '../contexts/TopicContext';

const PAGE_TITLE = 'Data Interview Prep by Role: Analyst, Engineer & Scientist | datathink';
const PAGE_DESC =
  'Compare data interview prep by role: Data Analyst, Data Engineer, Analytics Engineer, and Data Scientist, with SQL, product sense, ML, systems, samples, and mocks.';
const PAGE_URL = 'https://datathink.co/interview-prep';

const breadcrumbLd = {
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: [
    {
      '@type': 'ListItem',
      position: 1,
      name: 'Home',
      item: 'https://datathink.co/',
    },
    {
      '@type': 'ListItem',
      position: 2,
      name: 'Interview prep',
      item: PAGE_URL,
    },
  ],
};

const itemListLd = {
  '@context': 'https://schema.org',
  '@type': 'ItemList',
  itemListElement: ROLES.map((role, i) => ({
    '@type': 'ListItem',
    position: i + 1,
    name: `${role.label} Interview Prep`,
    url: `https://datathink.co/interview-prep/${role.slug}`,
  })),
};

export default function InterviewPrepIndexPage() {
  return (
    <div className="ip-page">
      <Helmet>
        <title>{PAGE_TITLE}</title>
        <meta name="description" content={PAGE_DESC} />
        <meta property="og:title" content={PAGE_TITLE} />
        <meta property="og:description" content={PAGE_DESC} />
        <meta property="og:url" content={PAGE_URL} />
        <link rel="canonical" href={PAGE_URL} />
        <script type="application/ld+json">{JSON.stringify(breadcrumbLd)}</script>
        <script type="application/ld+json">{JSON.stringify(itemListLd)}</script>
      </Helmet>

      <Topbar />

      <main className="ip-main">

        {/* ── BREADCRUMB ─────────────────────────────────────── */}
        <div className="lp-inner ip-breadcrumb-wrap">
          <nav className="ip-breadcrumb" aria-label="Breadcrumb">
            <Link to="/">datathink</Link>
            <span className="ip-breadcrumb-sep" aria-hidden="true">/</span>
            <span aria-current="page">Interview prep</span>
          </nav>
        </div>

        {/* ── HERO ───────────────────────────────────────────── */}
        <section className="lp-section ip-hero">
          <div className="lp-inner ip-hero-inner">
            <p className="lp-eyebrow">Interview prep</p>
            <h1 className="ip-h1">Data interview prep, by role</h1>
            <p className="ip-hero-sub">
              Data interviews usually test a mix of SQL, data manipulation, statistics, product metrics, experimentation, systems, modeling, and machine learning. The mix changes by role. Use these pages to see what each role tends to emphasize, how the tracks are weighted, and where to start with a free sample.
            </p>
          </div>
          <button
            type="button"
            className="ip-scroll-cue"
            aria-label="Scroll to content"
            onClick={(e) => e.currentTarget.closest('section')?.nextElementSibling?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
          </button>
        </section>

        {/* ── ROLE CARDS ─────────────────────────────────────── */}
        <section className="lp-section lp-section-rule ip-index-roles">
          <div className="lp-inner">
            <div className="ip-role-grid">
              {ROLES.map((role, index) => (
                <Reveal key={role.slug} delay={index * 60}>
                  <Link
                    to={`/interview-prep/${role.slug}`}
                    className="ip-role-card"
                  >
                    <h2 className="ip-role-card-heading">{role.label}</h2>
                    <div className="ip-role-card-tracks">
                      {role.tracks.map((trackSlug) => {
                        const meta = TRACK_META[trackSlug];
                        if (!meta) return null;
                        return (
                          <span key={trackSlug} className="ip-role-track-chip">
                            <span
                              className="ip-role-track-dot"
                              style={{ background: meta.color }}
                              aria-hidden="true"
                            />
                            <span className="ip-role-track-name">{meta.label}</span>
                          </span>
                        );
                      })}
                    </div>
                    <span className="ip-role-card-cta">View prep →</span>
                  </Link>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

      </main>

      {/* ── FOOTER ─────────────────────────────────────────────── */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <span className="landing-footer-copy">&copy; 2026 datathink</span>
          <nav className="landing-footer-links" aria-label="Legal">
            <a href="/guides">Guides</a>
            <Link to="/faq">FAQ</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms &amp; Conditions</Link>
            <Link to="/refund-policy">Refund Policy</Link>
            <Link to="/contact">Contact Us</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
