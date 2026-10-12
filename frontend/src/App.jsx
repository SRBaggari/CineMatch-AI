import { Route, Routes } from 'react-router-dom';
import Layout from './components/layout/Layout.jsx';
import AnalyticsPage from './pages/AnalyticsPage.jsx';
import BrowsePage from './pages/BrowsePage.jsx';
import HomePage from './pages/HomePage.jsx';
import HowItWorksPage from './pages/HowItWorksPage.jsx';
import MovieDetailsPage from './pages/MovieDetailsPage.jsx';
import MyListPage from './pages/MyListPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';
import PreferencesPage from './pages/PreferencesPage.jsx';
import ResultsPage from './pages/ResultsPage.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="preferences" element={<PreferencesPage />} />
        <Route path="recommendations" element={<ResultsPage />} />
        <Route path="movies/:movieId" element={<MovieDetailsPage />} />
        <Route path="browse" element={<BrowsePage />} />
        <Route path="my-list" element={<MyListPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="how-it-works" element={<HowItWorksPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
