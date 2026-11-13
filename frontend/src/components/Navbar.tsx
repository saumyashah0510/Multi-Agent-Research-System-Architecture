import { useState, useEffect } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import scholarisLogo from "../images/Scholaris_logo.png";
import { cn } from "../lib/utils";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const currentTab = (searchParams.get("tab") || "").toLowerCase();
  const isHome = location.pathname === "/";
  const { user, isAuthenticated, logout } = useAuth();

  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 15);
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const pathname = location.pathname.toLowerCase();
  const isPapers = currentTab === "papers" || pathname === "/papers";
  const isChat = currentTab === "chat" || pathname === "/chat";
  const isReport =
    !isChat &&
    (currentTab === "report" ||
      currentTab === "reports" ||
      pathname === "/report" ||
      pathname === "/reports" ||
      pathname.startsWith("/review"));
  const isResearch =
    !isHome &&
    !isPapers &&
    !isReport &&
    !isChat &&
    (currentTab === "research" ||
      pathname === "/dashboard" ||
      pathname === "/research");

  const navLinks = [
    {
      name: "Research",
      href: "/dashboard?tab=research",
      isActive: isResearch,
    },
    {
      name: "Papers",
      href: "/dashboard?tab=papers",
      isActive: isPapers,
    },
    {
      name: "Report",
      href: "/dashboard?tab=report",
      isActive: isReport,
    },

    {
      name: "Chat",
      href: "/dashboard?tab=chat",
      isActive: isChat,
    },
  ];

  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full transition-all duration-300",
        isScrolled
          ? "bg-[var(--color-surface)]/75 backdrop-blur-md border-b border-black/5 shadow-xs"
          : "bg-transparent border-b border-transparent shadow-none"
      )}
    >
      <nav
        className="w-full max-w-[var(--container-max-width)] mx-auto px-6 md:px-12 py-2.5 sm:py-3 flex items-center justify-between gap-4"
        aria-label="Main Navigation"
      >
        {/* Brand / Logo */}
        <Link
          to="/"
          className="inline-flex items-center gap-2.5 text-black no-underline select-none outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 rounded-md shrink-0"
        >
          <img
            src={scholarisLogo}
            alt="Scholaris Logo Emblem"
            className="w-7 h-7 sm:w-8 sm:h-8 object-contain"
          />
          <span
            className="font-sans-ui font-bold text-xl sm:text-2xl tracking-compact text-black"
            style={{ letterSpacing: "-0.04em" }}
          >
            Scholaris
          </span>
        </Link>

        {/* All Other Pages: Nav Links */}
        {!isHome && (
          <div className="flex items-center gap-2 sm:gap-3 md:gap-4 min-w-0">
            <div className="flex items-center gap-1 sm:gap-1.5 overflow-x-auto no-scrollbar py-0.5">
              {navLinks.map((link) => (
                <Link
                  key={link.name}
                  to={link.href}
                  style={{ borderRadius: "var(--radius-sm)" }}
                  className={cn(
                    "px-3 sm:px-3.5 py-1.5 text-sm sm:text-base tracking-compact transition-all duration-150 no-underline shrink-0 select-none",
                    link.isActive
                      ? "bg-white text-black font-semibold shadow-xs border border-black/10"
                      : "text-neutral-700 hover:text-black hover:bg-black/5 font-medium"
                  )}
                >
                  {link.name}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* User Auth Action (Issue FE-11) */}
        <div className="flex items-center gap-2 shrink-0">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-neutral-700 hidden sm:inline">
                {user.name || user.email.split("@")[0]}
              </span>
              <button
                onClick={logout}
                className="text-xs py-1.5 px-3 rounded-[var(--radius-sm)] border border-neutral-300 hover:bg-neutral-100 text-neutral-800 transition font-medium cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="text-xs sm:text-sm font-semibold py-2 px-4 rounded-[var(--radius-sm)] bg-neutral-900 text-white hover:bg-neutral-800 transition no-underline shadow-xs cursor-pointer"
            >
              Login
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
