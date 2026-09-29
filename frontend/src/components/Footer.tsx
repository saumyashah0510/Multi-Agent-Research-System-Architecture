import { Link } from "react-router-dom";
import scholarisLogo from "../images/Scholaris_logo.png";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer
      className="w-full pt-10 md:pt-12 pb-12 px-6 md:px-12 flex flex-col items-center mt-4 md:mt-6 border-t border-black/5 tracking-compact"
      style={{
        background: "var(--gradient-footer-bg)",
      }}
      aria-label="Site Footer"
    >
      <div className="w-full max-w-[var(--container-max-width)] mx-auto flex flex-col">
        {/* Top Section: Brand + Links Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-8 pb-12 border-b border-black/10">
          {/* Brand Column (2 cols on md) */}
          <div className="md:col-span-2 flex flex-col items-start space-y-4">
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
          <div className="flex flex-col space-y-3">
            <h4 className="font-sans-ui font-semibold text-xs uppercase tracking-wider text-neutral-900">
              Platform
            </h4>
            <ul className="space-y-2 text-sm text-neutral-600 font-sans-ui">
              <li>
                <Link to="/dashboard" className="hover:text-black transition-colors">
                  Research Console
                </Link>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-black transition-colors">
                  Discovery Engine
                </a>
              </li>
              <li>
                <a href="#review" className="hover:text-black transition-colors">
                  Paper Screening
                </a>
              </li>
              <li>
                <a href="#synthesis" className="hover:text-black transition-colors">
                  Synthesis Matrix
                </a>
              </li>
            </ul>
          </div>

          {/* Column 2: Resources */}
          <div className="flex flex-col space-y-3">
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
              <li>
                <a
                  href="https://github.com/saumyashah0510/Multi-Agent-Research-System-Architecture#readme"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-black transition-colors"
                >
                  Documentation
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Section: Copyright & Legal */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-neutral-500 font-sans-ui">
          <p>
            &copy; {currentYear} Scholaris AI. Human-in-the-Loop Literature Review Pipeline.
          </p>

          <div className="flex items-center space-x-6">
            <span className="hover:text-black cursor-pointer">
              Privacy Policy
            </span>
            <span className="hover:text-black cursor-pointer">
              Terms of Service
            </span>
            <span className="hover:text-black cursor-pointer">
              MIT License
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
