import { createContext, useContext, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';

// Prevent the browser from restoring a cached scroll position after client-side
// navigation — we manage scroll ourselves (e.g. hash anchors, page transitions).
if (typeof window !== 'undefined' && 'scrollRestoration' in history) {
  history.scrollRestoration = 'manual';
}
import { HelmetProvider } from 'react-helmet-async';
import { CatalogProvider } from './catalogContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { TopicProvider } from './contexts/TopicContext';
import { CatalogCountsProvider } from './contexts/CatalogCountsContext';
import AppShell from './components/AppShell';
import ErrorBoundary from './components/ErrorBoundary';
import AuthPage from './pages/AuthPage';
import NotFoundPage from './pages/NotFoundPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import LandingPage from './pages/LandingPage';
import MockHub from './pages/MockHub';
import MockSession from './pages/MockSession';
import ProgressDashboard from './pages/ProgressDashboard';
import QuestionPage from './pages/QuestionPage';
import SampleQuestionPage from './pages/SampleQuestionPage';
import SampleHubPage from './pages/SampleHubPage';
import { TRACK_META } from './trackRegistry';
import LearningPath from './pages/LearningPath';
import LearningPathsIndex from './pages/LearningPathsIndex';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import TermsPage from './pages/TermsPage';
import RefundPolicyPage from './pages/RefundPolicyPage';
import ContactPage from './pages/ContactPage';
import FAQPage from './pages/FAQPage';
import PricingPage from './pages/PricingPage';
import AccountPage from './pages/AccountPage';
import ToastViewport from './components/ToastViewport';
import { trackPageView } from './analytics';

// ── Theme ──────────────────────────────────────────────────────
export const ThemeContext = createContext(null);

export function useTheme() {
  return useContext(ThemeContext);
}

export const ToastContext = createContext(null);

export function useToast() {
  return useContext(ToastContext) ?? { notify: () => {} };
}

function ThemeProvider({ children }) {
  // LAUNCH: light-only. Dark mode is DEFERRED to a future version and sits
  // DORMANT — its [data-theme="dark"] CSS (App.css), the CodeEditor
  // forest/charcoal switch, and the isDark logo-src logic all remain in the
  // codebase but are unreachable because we lock `theme` to 'light' and `isDark`
  // to false here, so every consumer takes its light branch. We deliberately
  // ignore both localStorage and the OS prefers-color-scheme, and we FLUSH any
  // previously-stored `theme` so a returning dark-mode visitor lands on light.
  // Re-enabling dark is a near-one-line flip: restore the
  // localStorage/prefers-color-scheme read here AND in the index.html pre-paint
  // bootstrap script. See docs/decisions/DECISIONS.md (2026-06-17 defer-dark)
  // + docs/design/color-palette.md § Active theme launch status.
  const theme = 'light';

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'light');
    // Flush a stale theme preference left by a pre-launch (possibly dark) visitor,
    // so re-enabling dark later starts from the documented light default.
    if (localStorage.getItem('theme')) localStorage.removeItem('theme');
  }, []);

  // Context shape preserved so consumers (Topbar / SampleQuestionPage logo,
  // CodeEditor) don't break. isDark is permanently false; setTheme / cycleTheme
  // are intentional no-ops while dark is deferred.
  const isDark = false;
  const setTheme = () => {};
  const cycleTheme = () => {};
  const themeIcon = '☾';
  const themeLabel = 'Switch to dark mode';

  return (
    <ThemeContext.Provider value={{ theme, setTheme, isDark, cycleTheme, themeIcon, themeLabel }}>
      {children}
    </ThemeContext.Provider>
  );
}
// ──────────────────────────────────────────────────────────────

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  function dismissToast(id) {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }

  function notify(input) {
    const payload = typeof input === 'string' ? { title: input } : (input ?? {});
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const toast = {
      id,
      title: payload.title ?? '',
      message: payload.message ?? '',
      tone: payload.tone ?? 'info',
      durationMs: payload.durationMs ?? 3200,
    };
    setToasts((prev) => [...prev.slice(-3), toast]);

    window.setTimeout(() => {
      dismissToast(id);
    }, toast.durationMs);
  }

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

function RouteTransition({ children, transitionKey }) {
  const location = useLocation();
  useEffect(() => {
    trackPageView();
    // history.scrollRestoration is 'manual' so we own scroll-to-top on every
    // route change. Skip when a hash is present — the destination page owns
    // scrolling to its anchor.
    // Skip the reset when a hash anchor is present (the destination page owns its
    // scroll), when a modal is open over a background page (keep the background
    // where it was), or when a modal close asked to preserve scroll — so the
    // footer → policy → "Back to home" / Contact-modal-close flow returns the
    // user to the footer rather than the top.
    if (!location.hash && !location.state?.backgroundLocation && !location.state?.preserveScroll) {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }, [location.pathname]);
  return (
    <div key={transitionKey ?? `${location.pathname}${location.search}`} className="route-transition">
      {children}
    </div>
  );
}

function PolicyModal({ title, children, onClose }) {
  return (
    <div className="policy-overlay" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="policy-modal" onClick={(event) => event.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}

function AppRoutes() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const backgroundLocation = location.state?.backgroundLocation;

  // Consume upgrade intent that was saved to sessionStorage before an
  // OAuth redirect (where React Router state is lost). Fires once auth
  // resolves to a logged-in user after returning from the OAuth provider.
  useEffect(() => {
    if (authLoading || !user) return;
    const raw = sessionStorage.getItem('pendingUpgrade');
    if (!raw) return;
    sessionStorage.removeItem('pendingUpgrade');
    try {
      const { tier, returnTo } = JSON.parse(raw);
      navigate(returnTo || '/dashboard', { state: { upgradeTier: tier }, replace: true });
    } catch { /* malformed entry — already removed */ }
  }, [user, authLoading, navigate]);
  const routeLocation = backgroundLocation || location;
  const closePolicyModal = () => {
    if (backgroundLocation) {
      // Return to the background page (e.g. the landing footer) without jumping to
      // the top — preserveScroll tells RouteTransition to leave the scroll alone.
      navigate(`${backgroundLocation.pathname}${backgroundLocation.search}`, { replace: true, state: { preserveScroll: true } });
      return;
    }
    navigate(-1);
  };

  // Derive a stable key from the first two path segments so navigating
  // between questions within the same topic does NOT remount AppShell/SidebarNav.
  // Major transitions (landing→auth, sql→python, practice→dashboard) still remount.
  const segments = routeLocation.pathname.replace(/\/$/, '').split('/').filter(Boolean);
  const stableKey = segments.length >= 2 ? `/${segments[0]}/${segments[1]}` : `/${segments[0] ?? ''}`;

  return (
    <RouteTransition transitionKey={stableKey}>
      <Routes location={routeLocation}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/auth/reset-password" element={<ResetPasswordPage />} />
        <Route path="/auth/verify-email" element={<VerifyEmailPage />} />
        <Route path="/dashboard" element={<ProgressDashboard />} />
        <Route path="/mock" element={<AuthRequired><MockHub /></AuthRequired>} />
        <Route path="/mock/:id" element={<AuthRequired><MockSession /></AuthRequired>} />
        <Route path="/account" element={<AuthRequired><AccountPage /></AuthRequired>} />
        <Route path="/sample" element={<SampleHubPage />} />
        <Route path="/sample/:topic/:difficulty" element={<SampleQuestionPage />} />
        <Route path="/sample/:difficulty" element={<LegacySampleRedirect />} />

        {/* Legacy redirects — must come before the :topic wildcard */}
        <Route path="/practice/questions/:id" element={<LegacyQuestionRedirect />} />
        <Route path="/practice" element={<Navigate to="/practice/sql" replace />} />
        <Route path="/questions/:id" element={<LegacyQuestionRedirect />} />

        {/* python-data → pandas back-compat redirects (slug rename) */}
        <Route path="/practice/python-data" element={<Navigate to="/practice/pandas" replace />} />
        <Route path="/practice/python-data/questions/:id" element={<LegacyPythonDataPracticeRedirect />} />
        <Route path="/learn/python-data" element={<Navigate to="/learn/pandas" replace />} />
        <Route path="/learn/python-data/:slug" element={<LegacyPythonDataLearnRedirect />} />
        <Route path="/sample/python-data/:difficulty" element={<LegacyPythonDataSampleRedirect />} />

        {/* Policy pages */}
        <Route path="/privacy" element={<PrivacyPolicyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        <Route path="/refund-policy" element={<RefundPolicyPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="/faq" element={<FAQPage />} />
        <Route path="/pricing" element={<PricingPage />} />

        {/* Learning paths */}
        <Route path="/learn" element={<LearningPathsIndex />} />
        <Route path="/learn/:topic" element={<LearningPathsIndex />} />
        <Route path="/learn/:topic/:slug" element={<LearningPath />} />

        {/* Topic-aware practice routes */}
        <Route path="/practice/:topic" element={<TopicShell />}>
          <Route path="questions/:id" element={<QuestionPage />} />
        </Route>

        {/* 404 catch-all */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      {backgroundLocation && (
        <PolicyModal title="Policy" onClose={closePolicyModal}>
          <Routes>
            <Route path="/privacy" element={<PrivacyPolicyPage isModal />} />
            <Route path="/terms" element={<TermsPage isModal />} />
            <Route path="/refund-policy" element={<RefundPolicyPage isModal />} />
            <Route path="/contact" element={<ContactPage isModal />} />
          </Routes>
        </PolicyModal>
      )}
    </RouteTransition>
  );
}

function AuthRequired({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!user || user.email === null) return <Navigate to="/auth" state={{ from: location.pathname }} replace />;
  return children;
}

function TopicShell() {
  return (
    <TopicProvider>
      <CatalogProvider>
        <AppShell />
      </CatalogProvider>
    </TopicProvider>
  );
}

// Legacy redirect: /practice/questions/:id → /practice/sql/questions/:id
function LegacyQuestionRedirect() {
  const { id } = useParams();
  return <Navigate to={`/practice/sql/questions/${id}`} replace />;
}

// python-data → pandas back-compat redirects (slug rename 2026-06-09)
function LegacyPythonDataPracticeRedirect() {
  const { id } = useParams();
  return <Navigate to={`/practice/pandas/questions/${id}`} replace />;
}
function LegacyPythonDataLearnRedirect() {
  const { slug } = useParams();
  return <Navigate to={`/learn/pandas/${slug}`} replace />;
}
function LegacyPythonDataSampleRedirect() {
  const { difficulty } = useParams();
  return <Navigate to={`/sample/pandas/${difficulty}`} replace />;
}

// Legacy redirect: /sample/:difficulty → /sample/sql/:difficulty
// Also handles users guessing /sample/<topic> — redirects to /sample/<topic>/easy
// when the path segment matches a known track slug. Unknown segments fall back
// to the Sample Hub.
function LegacySampleRedirect() {
  const { difficulty } = useParams();
  if (difficulty === 'easy' || difficulty === 'medium' || difficulty === 'hard') {
    return <Navigate to={`/sample/sql/${difficulty}`} replace />;
  }
  if (TRACK_META[difficulty]) {
    return <Navigate to={`/sample/${difficulty}/easy`} replace />;
  }
  return <Navigate to="/sample" replace />;
}

export default function App() {
  return (
    <HelmetProvider>
    <ThemeProvider>
    <BrowserRouter>
      <AuthProvider>
        <CatalogCountsProvider>
        <ToastProvider>
          <ErrorBoundary>
            <AppRoutes />
          </ErrorBoundary>
        </ToastProvider>
        </CatalogCountsProvider>
      </AuthProvider>
    </BrowserRouter>
    </ThemeProvider>
    </HelmetProvider>
  );
}
