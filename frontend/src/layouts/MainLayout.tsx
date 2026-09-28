import { Outlet, useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function MainLayout() {
  const location = useLocation();
  const isHome = location.pathname === "/";

  // For the marketing landing page (/), render full-bleed without dark console margins or duplicate nav/footer
  if (isHome) {
    return <Outlet />;
  }

  // For app dashboard routes, apply the signature Scholaris light pastel gradient with prominent green
  return (
    <div
      id="main-layout"
      className="min-h-screen flex flex-col font-sans-ui text-neutral-900"
      style={{
        background:
          "linear-gradient(180deg, #DFFFAA 0%, #DFFFAA 55%, #EDFDE2 80%, #F6F8FB 100%)",
      }}
    >
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
        <Outlet />
      </main>
      <footer className="border-t border-black/5 py-6 text-center text-xs text-neutral-500">
        Scholaris AI — Human-in-the-Loop Multi-Agent Research System
      </footer>
    </div>
  );
}
