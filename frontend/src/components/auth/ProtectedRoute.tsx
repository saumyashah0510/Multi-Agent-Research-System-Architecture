import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import scholarisLogo from "../../images/Scholaris_logo.png";

export default function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center"
        style={{ background: "var(--gradient-auth-bg)" }}
      >
        <img
          src={scholarisLogo}
          alt="Scholaris Logo"
          className="w-10 h-10 object-contain animate-pulse mb-3"
        />
        <div className="w-6 h-6 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
