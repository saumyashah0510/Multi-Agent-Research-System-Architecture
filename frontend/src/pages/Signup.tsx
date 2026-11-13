/**
 * Signup Page
 *
 * Implements [FE-11] User Registration & Session Initialization
 * Styled with Scholaris split-screen design language matching Login.tsx:
 * - Left panel: Light green illustration canvas (Login_img.png)
 * - Right panel: Registration form with client-side validation,
 *   submit state, Google/GitHub sign-up, and error handling.
 */

import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, Eye, EyeOff } from "lucide-react";
import { FcGoogle } from "react-icons/fc";
import { FaGithub } from "react-icons/fa";
import { useAuth } from "../context/AuthContext";
import scholarisLogo from "../images/Scholaris_logo.png";
import loginImg from "../images/Login_img.png";

export default function Signup() {
  const navigate = useNavigate();
  const location = useLocation();
  const { register, isAuthenticated } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Helper to resolve saved destination or fallback
  const getDestination = () => {
    const from = (location.state as any)?.from;
    if (!from) return "/dashboard";
    if (typeof from === "string") return from;
    return `${from.pathname || ""}${from.search || ""}${from.hash || ""}` || "/dashboard";
  };

  // If already authenticated, navigate directly to destination or dashboard
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate(getDestination(), { replace: true });
    }
  }, [isAuthenticated, navigate, location.state]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email, password, name.trim() || undefined);
      navigate(getDestination(), { replace: true });
    } catch (err: any) {
      setError(err.message || "Failed to create account. Please verify your details.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSocial = () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setError("Google Sign-In is not configured in environment (VITE_GOOGLE_CLIENT_ID).");
      return;
    }
    const redirectUri = encodeURIComponent(`${window.location.origin}/auth/callback`);
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=openid%20email%20profile&prompt=select_account`;
  };

  const handleGitHubSocial = () => {
    const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID;
    if (!clientId) {
      setError("GitHub Sign-In is not configured in environment (VITE_GITHUB_CLIENT_ID).");
      return;
    }
    const redirectUri = encodeURIComponent(`${window.location.origin}/auth/callback`);
    window.location.href = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=user:email`;
  };

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center p-4 sm:p-6 md:p-8"
      style={{ background: "var(--gradient-auth-bg)" }}
    >
      <div className="w-full max-w-[880px] md:min-h-[520px] bg-white rounded-2xl shadow-2xl shadow-blue-900/10 overflow-hidden grid grid-cols-1 md:grid-cols-2 border border-white/60">
        {/* Left Side: Illustration Panel */}
        <div
          className="flex items-center justify-center relative overflow-hidden w-full h-full min-h-[300px] md:min-h-[520px]"
          style={{ background: "var(--tint-mint)" }}
        >
          <img
            src={loginImg}
            alt="Scholaris Research Illustration"
            className="w-full h-auto object-contain select-none"
          />
        </div>

        {/* Right Side: Registration Form */}
        <div className="p-8 sm:p-10 flex flex-col justify-center bg-white h-full">
          {/* Header / Brand */}
          <Link to="/" className="inline-flex items-center gap-2.5 mb-5 group no-underline">
            <img src={scholarisLogo} alt="Scholaris Logo" className="w-7 h-7 object-contain" />
            <span className="font-bold text-lg text-neutral-900 tracking-tight group-hover:text-emerald-700 transition">
              Scholaris
            </span>
          </Link>

          <h1 className="text-xl sm:text-2xl font-bold text-neutral-900 mb-5">
            Create an account
          </h1>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Dr. Alan Turing"
                style={{ background: "var(--color-surface)" }}
                className="w-full px-3.5 py-2.5 rounded-[var(--radius-sm)] border border-transparent text-sm text-neutral-800 placeholder-neutral-400 focus:bg-white focus:border-neutral-300 focus:outline-none transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="researcher@university.edu"
                style={{ background: "var(--color-surface)" }}
                className="w-full px-3.5 py-2.5 rounded-[var(--radius-sm)] border border-transparent text-sm text-neutral-800 placeholder-neutral-400 focus:bg-white focus:border-neutral-300 focus:outline-none transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-500 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password (min 6 characters)"
                  style={{ background: "var(--color-surface)" }}
                  className="w-full px-3.5 py-2.5 rounded-[var(--radius-sm)] border border-transparent text-sm text-neutral-800 placeholder-neutral-400 focus:bg-white focus:border-neutral-300 focus:outline-none pr-10 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition p-1"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              style={{ background: "var(--color-accent)" }}
              className="w-full py-2.5 px-4 rounded-[var(--radius-sm)] text-neutral-900 font-bold text-sm transition shadow-xs hover:opacity-90 disabled:opacity-60 cursor-pointer mt-2"
            >
              {isSubmitting ? "Creating account..." : "Sign Up"}
            </button>
          </form>

          {/* Social Sign Up Buttons */}
          <div className="grid grid-cols-2 gap-3 mt-4">
            <button
              type="button"
              onClick={handleGoogleSocial}
              className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-[var(--radius-sm)] bg-white hover:bg-neutral-50 text-neutral-800 text-xs font-semibold transition cursor-pointer border border-neutral-300 hover:border-neutral-400 shadow-xs"
            >
              <FcGoogle className="w-4 h-4 shrink-0 text-base" />
              <span className="truncate">Sign up with Google</span>
            </button>

            <button
              type="button"
              onClick={handleGitHubSocial}
              className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-[var(--radius-sm)] bg-white hover:bg-neutral-50 text-neutral-800 text-xs font-semibold transition cursor-pointer border border-neutral-300 hover:border-neutral-400 shadow-xs"
            >
              <FaGithub className="w-4 h-4 shrink-0 text-neutral-900 text-base" />
              <span className="truncate">Sign up with GitHub</span>
            </button>
          </div>

          {/* Error Message below Social Buttons */}
          {error && (
            <div className="mt-3 w-full p-2.5 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2 transition-all">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span className="leading-tight">{error}</span>
            </div>
          )}

          {/* Footer Navigation */}
          <p className="mt-4 text-center text-xs text-neutral-500">
            Already have an account?{" "}
            <Link
              to="/login"
              state={location.state}
              className="font-semibold text-neutral-900 hover:underline"
            >
              Log in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
