import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-900/80 border-b border-slate-800 text-slate-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Title */}
        <Link to="/" className="flex items-center space-x-3 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30 group-hover:scale-105 transition-transform">
            S
          </div>
          <div>
            <span className="font-extrabold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-indigo-300">
              Scholaris AI
            </span>
            <span className="ml-2 text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
              Multi-Agent
            </span>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="flex items-center space-x-1 sm:space-x-4">
          <Link
            to="/"
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
              isActive("/")
                ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40"
                : "text-slate-300 hover:text-white hover:bg-slate-800/60"
            }`}
          >
            Home
          </Link>
          <Link
            to="/dashboard"
            className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
              isActive("/dashboard")
                ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40"
                : "text-slate-300 hover:text-white hover:bg-slate-800/60"
            }`}
          >
            Research Dashboard
          </Link>
        </nav>

        {/* System Status Indicator */}
        <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700/60">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Pipeline Online</span>
        </div>
      </div>
    </header>
  );
}
