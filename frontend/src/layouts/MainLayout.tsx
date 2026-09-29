import { Outlet, useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

export default function MainLayout() {
  const location = useLocation();
  const isHome = location.pathname === "/";


  if (isHome) {
    return <Outlet />;
  }

  return (
    <div
      id="main-layout"
      className="min-h-screen flex flex-col font-sans-ui text-neutral-900"
      style={{
        backgroundColor: "var(--color-surface)",
        background: "var(--gradient-page-bg)",
      }}
    >
      <Navbar />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
