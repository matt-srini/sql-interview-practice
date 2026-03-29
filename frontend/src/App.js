import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom';
import { CatalogProvider } from './catalogContext';
import { AuthProvider } from './contexts/AuthContext';
import { TopicProvider } from './contexts/TopicContext';
import AppShell from './components/AppShell';
import AuthPage from './pages/AuthPage';
import LandingPage from './pages/LandingPage';
import ProgressDashboard from './pages/ProgressDashboard';
import QuestionPage from './pages/QuestionPage';
import SampleQuestionPage from './pages/SampleQuestionPage';

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
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/dashboard" element={<ProgressDashboard />} />
          <Route path="/sample/:topic/:difficulty" element={<SampleQuestionPage />} />
          <Route path="/sample/:difficulty" element={<LegacySampleRedirect />} />

          {/* Legacy redirects — must come before the :topic wildcard */}
          <Route path="/practice/questions/:id" element={<LegacyQuestionRedirect />} />
          <Route path="/practice" element={<Navigate to="/practice/sql" replace />} />
          <Route path="/questions/:id" element={<LegacyQuestionRedirect />} />

          {/* Topic-aware practice routes */}
          <Route path="/practice/:topic" element={<TopicShell />}>
            <Route path="questions/:id" element={<QuestionPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
