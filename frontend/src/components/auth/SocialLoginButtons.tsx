/**
 * SocialLoginButtons Component
 *
 * Implements [FE-12] OAuth 2.0 Social Login Integration
 * Provides one-click authentication triggers for:
 * - Continue with Google (OAuth 2.0 Authorization Endpoint)
 * - Continue with GitHub (OAuth 2.0 Authorize Endpoint)
 */

import { FcGoogle } from "react-icons/fc";
import { FaGithub } from "react-icons/fa";

export interface SocialLoginButtonsProps {
  onSuccess?: () => void;
  onError?: (err: string) => void;
  mode?: "signin" | "signup";
  returnTo?: string;
  className?: string;
}

export default function SocialLoginButtons({
  onError,
  mode = "signin",
  returnTo = "/dashboard",
  className = "grid grid-cols-2 gap-3",
}: SocialLoginButtonsProps) {
  const handleGoogleLogin = () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      if (onError) onError("Google Sign-In is not configured in environment (VITE_GOOGLE_CLIENT_ID).");
      return;
    }

    // Google OAuth 2.0 policy strictly forbids raw IP addresses in redirect URIs.
    // If user is accessing via a raw IP (e.g. 13.207.232.123), convert to .nip.io wildcard domain
    // so Google approves the OAuth security policy without manual user intervention.
    let baseOrigin = window.location.origin;
    const isRawIp = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(window.location.hostname);
    if (isRawIp) {
      baseOrigin = `${window.location.protocol}//${window.location.hostname}.nip.io${window.location.port ? `:${window.location.port}` : ""}`;
    }

    const redirectUri = encodeURIComponent(`${baseOrigin}/auth/callback`);
    const statePayload = { provider: "google", returnTo: returnTo || "/dashboard" };
    const encodedState = encodeURIComponent(JSON.stringify(statePayload));

    try {
      sessionStorage.setItem("oauth_redirect_info", JSON.stringify(statePayload));
    } catch {
      // sessionStorage might be restricted in private/incognito contexts
    }

    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=openid%20email%20profile&prompt=select_account&state=${encodedState}`;
    window.location.href = googleAuthUrl;
  };

  const handleGitHubLogin = () => {
    const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID;
    if (!clientId) {
      if (onError) onError("GitHub Sign-In is not configured in environment (VITE_GITHUB_CLIENT_ID).");
      return;
    }

    const redirectUri = encodeURIComponent(`${window.location.origin}/auth/callback`);
    const statePayload = { provider: "github", returnTo: returnTo || "/dashboard" };
    const encodedState = encodeURIComponent(JSON.stringify(statePayload));

    try {
      sessionStorage.setItem("oauth_redirect_info", JSON.stringify(statePayload));
    } catch {
      // sessionStorage might be restricted
    }

    const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=user:email&state=${encodedState}`;
    window.location.href = githubAuthUrl;
  };

  const googleLabel = mode === "signup" ? "Sign up with Google" : "Sign in with Google";
  const githubLabel = mode === "signup" ? "Sign up with GitHub" : "Sign in with GitHub";

  return (
    <div className={className}>
      <button
        type="button"
        onClick={handleGoogleLogin}
        aria-label={googleLabel}
        className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-[var(--radius-sm)] bg-white hover:bg-neutral-50 text-neutral-800 text-xs font-semibold transition cursor-pointer border border-neutral-300 hover:border-neutral-400 shadow-xs"
      >
        <FcGoogle className="w-4 h-4 shrink-0 text-base" />
        <span className="truncate">{googleLabel}</span>
      </button>

      <button
        type="button"
        onClick={handleGitHubLogin}
        aria-label={githubLabel}
        className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-[var(--radius-sm)] bg-white hover:bg-neutral-50 text-neutral-800 text-xs font-semibold transition cursor-pointer border border-neutral-300 hover:border-neutral-400 shadow-xs"
      >
        <FaGithub className="w-4 h-4 shrink-0 text-neutral-900 text-base" />
        <span className="truncate">{githubLabel}</span>
      </button>
    </div>
  );
}
