import { Link, useLocation, useSearchParams } from "react-router-dom";
import Button from "./Button";
import scholarisLogo from "../images/Scholaris_logo.png";
import { cn } from "../lib/utils";

const GitHubIcon = () => (
  <svg
    className="w-4 h-4"
    fill="currentColor"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      clipRule="evenodd"
    />
  </svg>
);

export default function Navbar() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const currentTab = searchParams.get("tab") || "research";
  const isDashboard =
    location.pathname === "/dashboard" || location.pathname === "/research";

  // All four options are clickable and land on the same research page (/dashboard)
  const navLinks = [
    {
      name: "Research",
      href: "/dashboard?tab=research",
      isActive: isDashboard && currentTab === "research",
    },
    {
      name: "Papers",
      href: "/dashboard?tab=papers",
      isActive: isDashboard && currentTab === "papers",
    },
    {
      name: "Chat",
      href: "/dashboard?tab=chat",
      isActive: isDashboard && currentTab === "chat",
    },
    {
      name: "Reports",
      href: "/dashboard?tab=reports",
      isActive: isDashboard && currentTab === "reports",
    },
  ];

  return (
    <header className="w-full bg-transparent">
      <nav
        className="w-full max-w-[var(--container-max-width)] mx-auto px-6 md:px-12 py-5 flex items-center justify-between gap-4"
        aria-label="Main Navigation"
      >
        <Link
          to="/"
          className="inline-flex items-center gap-2.5 text-black no-underline select-none outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 rounded-md shrink-0"
        >
          <img
            src={scholarisLogo}
            alt="Scholaris Logo Emblem"
            className="w-8 h-8 object-contain"
          />
          <span
            className="font-sans-ui font-bold text-xl tracking-compact text-black"
            style={{ letterSpacing: "-0.04em" }}
          >
            Scholaris
          </span>
        </Link>

        {/* All 4 options are active and clickable, landing on the same research page */}
        <div className="flex items-center gap-1 sm:gap-2">
          {navLinks.map((link) => (
            <Link
              key={link.name}
              to={link.href}
              className={cn(
                "px-3.5 sm:px-4 py-1.5 rounded-full text-xs sm:text-sm font-medium tracking-compact transition-colors no-underline",
                link.isActive
                  ? "bg-white text-black font-semibold shadow-xs border border-black/10"
                  : "text-neutral-700 hover:text-black hover:bg-black/5"
              )}
            >
              {link.name}
            </Link>
          ))}
        </div>

        <div className="hidden lg:block">
          <Button
            href="https://github.com/saumyashah0510/Multi-Agent-Research-System-Architecture"
            target="_blank"
            rel="noopener noreferrer"
            icon={<GitHubIcon />}
            iconPosition="right"
            ariaLabel="View Repository on GitHub"
            className="text-xs sm:text-sm"
          >
            <span className="hidden sm:inline">View Repository</span>
            <span className="sm:hidden">GitHub</span>
          </Button>
        </div>
      </nav>
    </header>
  );
}
