import { Link } from "react-router-dom";
import scholarisLogo from "../images/Scholaris_logo.png";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer
      className="w-full pt-6 sm:pt-8 pb-6 sm:pb-8 px-6 md:px-12 flex flex-col items-center border-t border-black/5 tracking-compact"
      style={{
        background: "var(--gradient-footer-bg)",
      }}
      aria-label="Site Footer"
    >
      <div className="w-full max-w-[var(--container-max-width)] mx-auto flex flex-col">
        {/* Top Section: Brand + Links Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 md:gap-8 pb-6 border-b border-black/10">
          {/* Brand Column (2 cols on md) */}
          <div className="md:col-span-2 flex flex-col items-start space-y-2.5">
            <Link
              to="/"
              className="inline-flex items-center gap-2.5 select-none outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 rounded-md"
            >
              <img
                src={scholarisLogo}
                alt="Scholaris Logo Emblem"
                className="w-7 h-7 object-contain"
              />
              <span className="font-sans-ui font-bold text-xl text-black">
                Scholaris
              </span>
            </Link>

            <p className="font-sans-ui text-sm text-neutral-600 max-w-sm leading-relaxed">
              Autonomous, human-in-the-loop multi-agent AI pipeline designed to
              accelerate deep academic literature reviews with verifiable citations.
            </p>
          </div>

          {/* Column 1: Platform */}
          <div className="flex flex-col space-y-2.5">
            <h4 className="font-sans-ui font-semibold text-xs uppercase tracking-wider text-neutral-900">
              Platform
            </h4>
            <ul className="space-y-2 text-sm text-neutral-600 font-sans-ui">
              <li>
                <Link to="/dashboard?tab=research" className="hover:text-black transition-colors">
                  Research
                </Link>
              </li>
              <li>
                <Link to="/dashboard?tab=papers" className="hover:text-black transition-colors">
                  Papers
                </Link>
              </li>
              <li>
                <Link to="/dashboard?tab=chat" className="hover:text-black transition-colors">
                  Chat
                </Link>
              </li>
              <li>
                <Link to="/dashboard?tab=reports" className="hover:text-black transition-colors">
                  Reports
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 2: Resources */}
          <div className="flex flex-col space-y-2.5">
            <h4 className="font-sans-ui font-semibold text-xs uppercase tracking-wider text-neutral-900">
              Resources
            </h4>
            <ul className="space-y-2 text-sm text-neutral-600 font-sans-ui">
              <li>
                <a
                  href="https://github.com/saumyashah0510/Multi-Agent-Research-System-Architecture"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-black transition-colors"
                >
                  GitHub Repository
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Section: Copyright */}
        <div className="pt-4 sm:pt-5 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-neutral-500 font-sans-ui">
          <p>
            &copy; {currentYear} Scholaris AI. Human-in-the-Loop Literature Review Pipeline.
          </p>
        </div>
      </div>
    </footer>
  );
}
