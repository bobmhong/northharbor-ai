import { Routes, Route } from "react-router-dom";
import Layout from "./components/ui/Layout";
import HomePage from "./pages/HomePage";
import InterviewPage from "./pages/InterviewPage";
import DashboardPage from "./pages/DashboardPage";
import ReportPage from "./pages/ReportPage";
import PlanListPage from "./pages/PlanListPage";
import QuickReviewPage from "./pages/QuickReviewPage";
import AdminAnalyticsPage from "./pages/AdminAnalyticsPage";
import AboutPage from "./pages/AboutPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/plans" element={<PlanListPage />} />
        <Route path="/interview" element={<InterviewPage />} />
        <Route path="/interview/:planId" element={<InterviewPage />} />
        <Route path="/review/:planId" element={<QuickReviewPage />} />
        <Route path="/dashboard/:planId" element={<DashboardPage />} />
        <Route path="/report/:reportId" element={<ReportPage />} />
        <Route path="/about" element={<AboutPage />} />
        {import.meta.env.DEV && (
          <Route path="/admin/analytics" element={<AdminAnalyticsPage />} />
        )}
      </Route>
    </Routes>
  );
}
