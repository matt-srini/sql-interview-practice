import { createContext, useContext, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { CatalogProvider } from './catalogContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { TopicProvider } from './contexts/TopicContext';
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
import LearningPath from './pages/LearningPath';
import LearningPathsIndex from './pages/LearningPathsIndex';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';
import TermsPage from './pages/TermsPage';
import RefundPolicyPage from './pages/RefundPolicyPage';
import ContactPage from './pages/ContactPage';
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

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => localStorage.getItem('theme') || getSystemTheme());

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  function setTheme(value) {
    setThemeState(value);
    localStorage.setItem('theme', value);
  }

  const isDark = theme === 'dark';
  const cycleTheme = () => setTheme(isDark ? 'light' : 'dark');
  const themeIcon = isDark ? '☀' : '☾';
  const themeLabel = isDark ? 'Switch to light mode' : 'Switch to dark mode';

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

function RouteTransition({ children }) {
  const location = useLocation();
  useEffect(() => { trackPageView(); }, [location.pathname]);
  return (
    <div key={`${location.pathname}${location.search}`} className="route-transition">
      {children}
    </div>
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

// Legacy redirect: /sample/:difficulty → /sample/sql/:difficulty
function LegacySampleRedirect() {
  const { difficulty } = useParams();
  return <Navigate to={`/sample/sql/${difficulty}`} replace />;
}

export default function App() {
  return (
    <HelmetProvider>
    <ThemeProvider>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <ErrorBoundary>
            <RouteTransition>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/auth" element={<AuthPage />} />
                <Route path="/auth/reset-password" element={<ResetPasswordPage />} />
                <Route path="/auth/verify-email" element={<VerifyEmailPage />} />
                <Route path="/dashboard" element={<ProgressDashboard />} />
                <Route path="/mock" element={<AuthRequired><MockHub /></AuthRequired>} />
                <Route path="/mock/:id" element={<AuthRequired><MockSession /></AuthRequired>} />
                <Route path="/sample/:topic/:difficulty" element={<SampleQuestionPage />} />
                <Route path="/sample/:difficulty" element={<LegacySampleRedirect />} />

                {/* Legacy redirects — must come before the :topic wildcard */}
                <Route path="/practice/questions/:id" element={<LegacyQuestionRedirect />} />
                <Route path="/practice" element={<Navigate to="/practice/sql" replace />} />
                <Route path="/questions/:id" element={<LegacyQuestionRedirect />} />

                {/* Policy pages */}
                <Route path="/privacy"       element={<PrivacyPolicyPage />} />
                <Route path="/terms"         element={<TermsPage />} />
                <Route path="/refund-policy" element={<RefundPolicyPage />} />
                <Route path="/contact"       element={<ContactPage />} />

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
            </RouteTransition>
          </ErrorBoundary>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
    </ThemeProvider>
    </HelmetProvider>
  );
}
