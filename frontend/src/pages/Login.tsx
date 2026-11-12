/**
 * Login Page
 *
 * Assignee Task (Issue FE-11):
 * - Render email & password sign-in form with validation.
 * - Call login() from useAuth().
 * - Redirect to /dashboard upon successful login.
 * - Render social login buttons (Google & GitHub) as placeholders for Issue FE-12.
 */

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import scholarisLogo from "../images/Scholaris_logo.png";
import SocialLoginButtons from "../components/auth/SocialLoginButtons";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      // TODO (Assignee - FE-11): Call login(email, password) and navigate to "/dashboard"
      await login(email, password);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-surface text-neutral-900">
      <div className="w-full max-w-md bg-white/80 backdrop-blur-md rounded-2xl border border-neutral-200/80 shadow-card p-8">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-block mb-3">
            <img src={scholarisLogo} alt="Scholaris Logo" className="h-10 mx-auto object-contain" />
          </Link>
          <h2 className="font-serif-heading text-2xl font-bold tracking-tight text-neutral-900">
            Welcome back
          </h2>
          <p className="text-sm text-neutral-500 mt-1">
            Sign in to access your literature reviews and research synthesis
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-600 mb-1">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="researcher@university.edu"
              className="w-full px-3.5 py-2.5 rounded-xl border border-neutral-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-600 transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-neutral-600 mb-1">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 rounded-xl border border-neutral-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-600 transition"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-2.5 px-4 rounded-xl bg-neutral-900 hover:bg-neutral-800 text-white font-medium text-sm transition shadow-sm hover:shadow disabled:opacity-50"
          >
            {isSubmitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-neutral-200" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-white px-3 text-neutral-400 font-medium">Or continue with</span>
          </div>
        </div>

        {/* Social Buttons */}
        <SocialLoginButtons onError={setError} />

        {/* Footer Link */}
        <p className="mt-8 text-center text-xs text-neutral-500">
          Don't have an account?{" "}
          <Link to="/signup" className="font-semibold text-emerald-700 hover:text-emerald-800 underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
