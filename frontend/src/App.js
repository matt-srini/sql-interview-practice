import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom';
import { CatalogProvider } from './catalogContext';
import AppShell from './components/AppShell';
import LandingPage from './pages/LandingPage';
import QuestionPage from './pages/QuestionPage';
import SampleQuestionPage from './pages/SampleQuestionPage';

function PracticeShell() {
  return (
    <CatalogProvider>
      <AppShell />
    </CatalogProvider>
  );
}

function LegacyQuestionRedirect() {
  const { id } = useParams();
  return <Navigate to={`/practice/questions/${id}`} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/sample/:difficulty" element={<SampleQuestionPage />} />
        <Route path="/practice" element={<PracticeShell />}>
          <Route path="questions/:id" element={<QuestionPage />} />
        </Route>
        <Route path="/questions/:id" element={<LegacyQuestionRedirect />} />
      </Routes>
    </BrowserRouter>
  );
}
