import { Routes, Route } from "react-router-dom";

import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Athletes from "./pages/Athletes";
import Assessments from "./pages/Assessments";
import VideoAnalysis from "./pages/VideoAnalysis";
import AnalysisHistory from "./pages/AnalysisHistory";
import AnalysisReport from "./pages/AnalysisReport";
import Notifications from "./pages/Notifications";
import Reports from "./pages/Reports";
import NotFound from "./pages/NotFound";

import ProtectedRoute from "./components/ProtectedRoute";
import Navbar from "./components/Navbar";

// Roles definition for route protection
const STAFF_ROLES = [
  "Coach",
  "Physiotherapist",
  "Sports Scientist",
  "Administrator",
];

function App() {
  return (
    <>
      <Navbar />

      <Routes>
        <Route path="/" element={<Landing />} />

        <Route path="/login" element={<Login />} />

        <Route path="/register" element={<Register />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/notifications"
          element={
            <ProtectedRoute>
              <Notifications />
            </ProtectedRoute>
          }
        />

        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />

        <Route
          path="/athletes"
          element={
            <ProtectedRoute allowedRoles={STAFF_ROLES}>
              <Athletes />
            </ProtectedRoute>
          }
        />

        <Route
          path="/assessments"
          element={
            <ProtectedRoute allowedRoles={STAFF_ROLES}>
              <Assessments />
            </ProtectedRoute>
          }
        />

        <Route
          path="/reports"
          element={
            <ProtectedRoute>
              <Reports />
            </ProtectedRoute>
          }
        />

        {/* Upload + live analysis */}
        <Route
          path="/analysis"
          element={
            <ProtectedRoute allowedRoles={["Athlete"]}>
              <VideoAnalysis />
            </ProtectedRoute>
          }
        />

        {/* Analysis history list — must come before /analysis/:videoId */}
        <Route
          path="/analysis/history"
          element={
            <ProtectedRoute allowedRoles={["Athlete"]}>
              <AnalysisHistory />
            </ProtectedRoute>
          }
        />

        {/* Historical analysis report (read-only) */}
        <Route
          path="/analysis/:videoId"
          element={
            <ProtectedRoute allowedRoles={["Athlete", ...STAFF_ROLES]}>
              <AnalysisReport />
            </ProtectedRoute>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}

export default App;