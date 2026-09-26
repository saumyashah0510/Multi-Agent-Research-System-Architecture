import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div id="home-page" className="py-12 sm:py-16 lg:py-20 flex flex-col items-center">
      {/* Hero Section */}
      <div className="text-center max-w-4xl mx-auto space-y-6">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold tracking-wide">
          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
          <span>Next-Gen Academic Literature Review</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-indigo-200 leading-tight">
          Automate Deep Academic Reviews with Multi-Agent AI
        </h1>

        <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Scholaris orchestrates autonomous search agents, relevance filters, and human-in-the-loop approvals to produce rigorous research reviews in minutes.
        </p>

        {/* CTA Actions */}
        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/dashboard"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-semibold shadow-lg shadow-indigo-500/25 transition-all transform hover:-translate-y-0.5 text-center"
          >
            Get Started →
          </Link>
          <a
            href="https://github.com/saumyashah0510/Multi-Agent-Research-System-Architecture"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full sm:w-auto px-6 py-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 font-medium transition-all text-center"
          >
            View Repository
          </a>
        </div>
      </div>

      {/* Feature Grid */}
      <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8 w-full">
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition-all">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-xl font-bold mb-4">
            🔍
          </div>
          <h3 className="text-lg font-semibold text-slate-100 mb-2">Multi-Source Search</h3>
          <p className="text-sm text-slate-400">
            Search arXiv, PubMed, and OpenAlex simultaneously with query expansion and semantic deduplication.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition-all">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center text-xl font-bold mb-4">
            👤
          </div>
          <h3 className="text-lg font-semibold text-slate-100 mb-2">Human-in-the-Loop</h3>
          <p className="text-sm text-slate-400">
            Interactively review, filter, and approve candidate papers before synthesis for full research control.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-indigo-500/40 transition-all">
          <div className="w-12 h-12 rounded-xl bg-pink-500/10 text-pink-400 flex items-center justify-center text-xl font-bold mb-4">
            📝
          </div>
          <h3 className="text-lg font-semibold text-slate-100 mb-2">Structured Synthesis</h3>
          <p className="text-sm text-slate-400">
            Generate detailed literature reviews with methodology matrices, research gaps, and formatted citations.
          </p>
        </div>
      </div>
    </div>
  );
}
