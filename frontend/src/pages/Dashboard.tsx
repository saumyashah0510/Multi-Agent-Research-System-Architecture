import ResearchInput from "../components/ResearchInput";
import ResearchFilters from "../components/ResearchFilters";

export default function Dashboard() {


  return (
    <div id="dashboard-page" className="space-y-8">
      {/* Dashboard Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100">
            Research Pipeline Console
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Initiate automated deep literature reviews, inspect agent reasoning, and approve papers.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <span className="px-3 py-1 rounded-md text-xs font-mono bg-slate-900 border border-slate-800 text-slate-300">
            Session: Idle
          </span>
        </div>
      </div>

      {/* Top Controls Container */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-6">
        <ResearchInput />
        <ResearchFilters />
      </div>

      {/* Main Workspace Grid (Papers Grid + Live Agent Log Sidebar) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Candidate Papers Container */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-200">Discovered & Screened Papers</h2>
            <span className="text-xs text-slate-500">0 papers selected</span>
          </div>

          <div className="p-12 rounded-2xl border-2 border-dashed border-slate-800 text-center bg-slate-900/30">
            <div className="w-12 h-12 mx-auto rounded-full bg-slate-800 flex items-center justify-center text-slate-400 mb-3">
              📚
            </div>
            <h3 className="text-sm font-medium text-slate-300">No Active Literature Search</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Enter a research topic above to launch the multi-agent search and screening workflow.
            </p>
          </div>
        </div>

        {/* Agent Activity Feed Sidebar */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-200">Live Agent Pipeline Log</h2>
          <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 font-mono text-xs space-y-3 min-h-[320px]">
            <div className="text-slate-500 border-b border-slate-800/80 pb-2 flex items-center justify-between">
              <span>Agent Event Log</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            </div>
            <div className="text-slate-400">
              <span className="text-slate-600">[00:00:00]</span> System initialized and awaiting user prompt.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
