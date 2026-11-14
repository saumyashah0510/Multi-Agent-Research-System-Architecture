import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import ReviewDetail from "./pages/ReviewDetail";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import AuthCallback from "./pages/AuthCallback";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/auth/callback" element={<AuthCallback />} />

          {/* Main App Routes */}
          <Route element={<MainLayout />}>
            {/* Public Home Route */}
            <Route index element={<Home />} />

            {/* Authenticated Protected Routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="research" element={<Dashboard />} />
              <Route path="review/:reviewId" element={<ReviewDetail />} />
              <Route path="reviews/:reviewId" element={<ReviewDetail />} />
              <Route path="papers" element={<Dashboard />} />
              <Route path="chat" element={<Dashboard />} />
              <Route path="reports" element={<Dashboard />} />
              <Route path="report" element={<Dashboard />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
