import { Outlet, useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function MainLayout() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  // For the marketing landing page (/), render full-bleed without dark console margins or duplicate nav/footer
  if (isHome) {
    return <Outlet />;
  }

  // For app dashboard routes, use the dark console frame
  return (
    <div
      id="main-layout"
      className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased"
    >
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        Scholaris AI — Human-in-the-Loop Multi-Agent Research System
      </footer>
    </div>
  );
}
