import { useState, useEffect, useRef } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { FiUser, FiLogOut } from "react-icons/fi";
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
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const signOutBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 15);
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Dismiss user account popover on outside click or Escape key press (returning focus to trigger)
  useEffect(() => {
    if (!isMenuOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        popoverRef.current &&
        !popoverRef.current.contains(target) &&
        triggerRef.current &&
        !triggerRef.current.contains(target)
      ) {
        setIsMenuOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsMenuOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMenuOpen]);

  // Move focus to the Sign Out button when user menu popover opens
  useEffect(() => {
    if (isMenuOpen) {
      requestAnimationFrame(() => {
        signOutBtnRef.current?.focus();
      });
    }
  }, [isMenuOpen]);

  // Close menu on navigation
  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname, location.search]);

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

        {/* User Auth Action (Issue FE-11 & Popover) */}
        <div className="relative flex items-center gap-2 shrink-0">
          {isAuthenticated && user ? (
            <div className="relative">
              <button
                ref={triggerRef}
                type="button"
                onClick={() => setIsMenuOpen((prev) => !prev)}
                aria-label="User menu"
                aria-expanded={isMenuOpen}
                aria-haspopup="menu"
                style={{
                  borderRadius: "var(--radius-pill)",
                  color: "var(--text-primary)",
                  backgroundColor: "var(--surface-card)",
                  border: "1px solid var(--border-default)",
                  boxShadow: "var(--shadow-2xs)",
                }}
                className={cn(
                  "w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center transition-all cursor-pointer select-none outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2",
                  isMenuOpen
                    ? "ring-2 ring-neutral-900/10 border-neutral-400"
                    : "hover:bg-[var(--surface-muted)] hover:border-neutral-300"
                )}
              >
                <FiUser className="w-4 h-4 text-neutral-900 stroke-[2]" />
              </button>

              {/* User Account Popover */}
              {isMenuOpen && (
                <div
                  ref={popoverRef}
                  role="menu"
                  aria-label="User account menu"
                  style={{
                    backgroundColor: "var(--surface-card)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-lg)",
                    boxShadow: "var(--shadow-container)",
                  }}
                  className="absolute right-0 top-full mt-2 w-64 p-2.5 z-50 animate-in fade-in slide-in-from-top-2 zoom-in-95 duration-150 flex flex-col gap-1.5 select-none"
                >
                  {/* Polished User Profile Header Card */}
                  <div
                    style={{
                      backgroundColor: "var(--brand-subtle)",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-subtle)",
                    }}
                    className="p-3 flex items-center gap-3"
                  >
                    <div
                      style={{
                        backgroundColor: "var(--tint-mint)",
                        border: "1px solid var(--mint-dark)",
                        borderRadius: "var(--radius-pill)",
                        color: "var(--mint-dark)",
                      }}
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 font-sans font-bold text-sm select-none"
                    >
                      {user.name
                        ? user.name.charAt(0).toUpperCase()
                        : user.email?.charAt(0).toUpperCase() || "U"}
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                      <span
                        style={{ color: "var(--text-primary)" }}
                        className="font-sans text-sm font-semibold tracking-compact truncate leading-snug"
                        title={user.name || "User"}
                      >
                        {user.name || user.email.split("@")[0]}
                      </span>
                      <span
                        style={{ color: "var(--text-secondary)" }}
                        className="font-sans text-xs truncate mt-0.5"
                        title={user.email}
                      >
                        {user.email}
                      </span>
                    </div>
                  </div>

                  {/* Subtle Divider */}
                  <div
                    style={{ borderTop: "1px solid var(--border-subtle)" }}
                    className="my-0.5"
                  />

                  {/* Refined Action Area & Sign Out Button */}
                  <button
                    ref={signOutBtnRef}
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setIsMenuOpen(false);
                      logout();
                    }}
                    style={{
                      borderRadius: "var(--radius-sm)",
                      fontFamily: "var(--font-sans)",
                    }}
                    className="group w-full flex items-center justify-between px-3 py-2 text-sm font-medium tracking-compact text-[var(--text-primary)] hover:text-[var(--status-error)] hover:bg-[color-mix(in_srgb,var(--status-error)_10%,transparent)] focus:bg-[color-mix(in_srgb,var(--status-error)_10%,transparent)] focus:text-[var(--status-error)] transition-colors duration-150 cursor-pointer outline-none"
                  >
                    <span>Sign Out</span>
                    <FiLogOut className="w-4 h-4 text-[var(--text-secondary)] group-hover:text-[var(--status-error)] group-focus:text-[var(--status-error)] transition-colors" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link
              to="/login"
              style={{ borderRadius: "var(--radius-sm)" }}
              className="text-xs sm:text-sm font-semibold py-2 px-4 bg-neutral-900 text-white hover:bg-neutral-800 transition no-underline shadow-xs cursor-pointer"
            >
              Login
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
