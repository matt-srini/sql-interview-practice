import { createContext, useContext, useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom';
import { CatalogProvider } from './catalogContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { TopicProvider } from './contexts/TopicContext';
import AppShell from './components/AppShell';
import AuthPage from './pages/AuthPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import LandingPage from './pages/LandingPage';
import MockHub from './pages/MockHub';
import MockSession from './pages/MockSession';
import ProgressDashboard from './pages/ProgressDashboard';
import QuestionPage from './pages/QuestionPage';
import SampleQuestionPage from './pages/SampleQuestionPage';
import LearningPath from './pages/LearningPath';
import LearningPathsIndex from './pages/LearningPathsIndex';

// ── Theme ──────────────────────────────────────────────────────
export const ThemeContext = createContext(null);

export function useTheme() {
  return useContext(ThemeContext);
}

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => localStorage.getItem('theme') || 'system');

  // Resolved = what is actually applied (accounts for system preference)
  const resolvedTheme = theme === 'system' ? getSystemTheme() : theme;

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', theme);
    }
  }, [theme]);

  // Keep resolved theme in sync when system preference changes
  useEffect(() => {
    if (theme !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setThemeState('system'); // re-render to pick up new resolved value
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  function setTheme(value) {
    setThemeState(value);
    if (value === 'system') {
      localStorage.removeItem('theme');
    } else {
      localStorage.setItem('theme', value);
    }
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
// ──────────────────────────────────────────────────────────────

function AuthRequired({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user || user.email === null) return <Navigate to="/auth" replace />;
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
    <ThemeProvider>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/auth/reset-password" element={<ResetPasswordPage />} />
          <Route path="/dashboard" element={<ProgressDashboard />} />
          <Route path="/mock" element={<AuthRequired><MockHub /></AuthRequired>} />
          <Route path="/mock/:id" element={<AuthRequired><MockSession /></AuthRequired>} />
          <Route path="/sample/:topic/:difficulty" element={<SampleQuestionPage />} />
          <Route path="/sample/:difficulty" element={<LegacySampleRedirect />} />

          {/* Legacy redirects — must come before the :topic wildcard */}
          <Route path="/practice/questions/:id" element={<LegacyQuestionRedirect />} />
          <Route path="/practice" element={<Navigate to="/practice/sql" replace />} />
          <Route path="/questions/:id" element={<LegacyQuestionRedirect />} />

          {/* Learning paths */}
          <Route path="/learn" element={<LearningPathsIndex />} />
          <Route path="/learn/:topic" element={<LearningPathsIndex />} />
          <Route path="/learn/:topic/:slug" element={<LearningPath />} />

          {/* Topic-aware practice routes */}
          <Route path="/practice/:topic" element={<TopicShell />}>
            <Route path="questions/:id" element={<QuestionPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
    </ThemeProvider>
  );
}
