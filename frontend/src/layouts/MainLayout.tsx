import { Outlet, useLocation } from "react-router-dom";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import { cn } from "../lib/utils";

export default function MainLayout() {
  const location = useLocation();
  const isHome = location.pathname === "/";
  const searchParams = new URLSearchParams(location.search);
  const hasReviewId = Boolean(searchParams.get("review_id"));
  const isChatWorkspace =
    (location.pathname.toLowerCase() === "/chat" ||
      (searchParams.get("tab") || "").toLowerCase() === "chat") &&
    hasReviewId;

  if (isHome) {
    return <Outlet />;
  }

  return (
    <div
      id="main-layout"
      className={cn(
        "flex flex-col font-sans-ui text-neutral-900",
        isChatWorkspace ? "h-screen max-h-screen overflow-hidden" : "min-h-screen"
      )}
      style={{
        backgroundColor: "var(--color-surface)",
        background: "var(--gradient-page-bg)",
      }}
    >
      <Navbar />
      <main className={cn("flex-1 w-full flex flex-col min-h-0", isChatWorkspace && "overflow-hidden")}>
        <Outlet />
      </main>
      {!isChatWorkspace && <Footer />}
    </div>
  );
}
