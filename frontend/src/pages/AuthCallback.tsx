/**
 * AuthCallback Page
 *
 * Implements [FE-12] OAuth 2.0 Social Login Integration & Callback Handler
 * - Intercepts OAuth redirect returns at /auth/callback.
 * - Extracts and checks authorization codes or credentials and provider errors.
 * - Resolves provider and return destination via state or session storage.
 * - Exchanges token with backend endpoints (authWithGoogle or authWithGitHub).
 * - Updates AuthContext with session credentials and redirects to intended destination.
 */

import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { authWithGitHub, authWithGoogle } from "../lib/api";
import { AuthResponse } from "../types";
import scholarisLogo from "../images/Scholaris_logo.png";

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setSession } = useAuth();

  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("Authenticating with provider...");

  const isMountedRef = useRef(true);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasProcessedRef = useRef(false);

  useEffect(() => {
    isMountedRef.current = true;

    // Avoid double-processing in React 18 StrictMode (which mounts effects twice in dev)
    if (hasProcessedRef.current) {
      return () => {
        isMountedRef.current = false;
        if (timerRef.current) {
          clearTimeout(timerRef.current);
          timerRef.current = null;
        }
      };
    }
    hasProcessedRef.current = true;

    const processCallback = async () => {
      // 1. Check for error returned by OAuth provider (e.g., user cancelled)
      const oauthError = searchParams.get("error_description") || searchParams.get("error");
      if (oauthError) {
        if (!isMountedRef.current) return;
        setError(`Authentication denied: ${oauthError}`);
        return;
      }

      const code = searchParams.get("code");
      const credential = searchParams.get("credential");
      const stateParam = searchParams.get("state");

      // 2. Resolve destination and provider hint from state or sessionStorage
      let providerHint: string | null = null;
      let returnTo = "/dashboard";

      if (stateParam) {
        try {
          // searchParams.get("state") has already percent-decoded the parameter
          const parsedState = JSON.parse(stateParam);
          if (parsedState.provider) providerHint = parsedState.provider;
          if (parsedState.returnTo) returnTo = parsedState.returnTo;
        } catch {
          // Fallback if state is raw string or not JSON
          if (stateParam.includes("google")) providerHint = "google";
          if (stateParam.includes("github")) providerHint = "github";
        }
      }

      if (!providerHint) {
        try {
          const stored = sessionStorage.getItem("oauth_redirect_info");
          if (stored) {
            const parsedStored = JSON.parse(stored);
            if (parsedStored.provider) providerHint = parsedStored.provider;
            if (parsedStored.returnTo) returnTo = parsedStored.returnTo;
          }
        } catch {
          // ignore storage read errors
        }
      }

      // Check URL clues if provider is still unknown
      if (!providerHint) {
        const scope = searchParams.get("scope");
        if (scope && (scope.includes("google") || scope.includes("openid"))) {
          providerHint = "google";
        }
      }

      if (!code && !credential) {
        if (!isMountedRef.current) return;
        setError("Missing authorization parameters. Please try signing in again.");
        return;
      }

      try {
        let authData: AuthResponse | null = null;

        if (credential) {
          // Google Identity Services (ID Token JWT)
          if (!isMountedRef.current) return;
          setStatusMessage("Verifying Google account credentials...");
          authData = await authWithGoogle(credential);
        } else if (code) {
          // Authorization code exchange
          if (providerHint === "github") {
            if (!isMountedRef.current) return;
            setStatusMessage("Exchanging GitHub authorization code...");
            try {
              authData = await authWithGitHub(code);
            } catch {
              // Fallback to Google if GitHub exchange throws
              if (!isMountedRef.current) return;
              setStatusMessage("Exchanging Google authorization code...");
              authData = await authWithGoogle(undefined, code);
            }
          } else if (providerHint === "google") {
            if (!isMountedRef.current) return;
            setStatusMessage("Exchanging Google authorization code...");
            authData = await authWithGoogle(undefined, code);
          } else {
            // Unknown provider: attempt GitHub first, then fallback to Google
            if (!isMountedRef.current) return;
            setStatusMessage("Exchanging authorization code...");
            try {
              authData = await authWithGitHub(code);
            } catch {
              authData = await authWithGoogle(undefined, code);
            }
          }
        }

        if (!isMountedRef.current) return;

        if (authData && authData.access_token) {
          try {
            sessionStorage.removeItem("oauth_redirect_info");
          } catch {
            // ignore
          }

          setSession(authData.access_token, authData.user);
          setStatusMessage("Authentication successful! Redirecting to research dashboard...");
          timerRef.current = setTimeout(() => {
            if (isMountedRef.current) {
              navigate(returnTo || "/dashboard", { replace: true });
            }
          }, 350);
        } else {
          throw new Error("Invalid response received from authentication service.");
        }
      } catch (err: any) {
        if (!isMountedRef.current) return;
        console.error("OAuth callback error:", err);
        try {
          sessionStorage.removeItem("oauth_redirect_info");
        } catch {
          // ignore
        }
        setError(err.message || "Failed to complete authentication. Please try again.");
      }
    };

    processCallback();

    return () => {
      isMountedRef.current = false;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [searchParams, navigate, setSession]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-surface text-neutral-900">
      <div className="w-full max-w-md bg-white/90 backdrop-blur-md rounded-2xl border border-neutral-200/80 shadow-card p-8 text-center">
        <Link to="/" className="inline-flex items-center gap-2 mb-4 justify-center">
          <img src={scholarisLogo} alt="Scholaris Logo" className="h-8 object-contain" />
          <span className="font-bold text-lg text-neutral-900 tracking-tight">Scholaris</span>
        </Link>

        {error ? (
          <div>
            <div className="p-3 mb-5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2.5 text-left">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600 mt-0.5" />
              <div className="flex-1 leading-relaxed">{error}</div>
            </div>
            <Link
              to="/login"
              className="inline-block w-full py-2.5 px-4 rounded-[var(--radius-sm)] bg-neutral-900 text-white text-xs font-semibold hover:bg-neutral-800 transition"
            >
              Back to Sign In
            </Link>
          </div>
        ) : (
          <div>
            <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h3 className="font-serif-heading text-base font-semibold text-neutral-900 mb-1">
              Signing you in
            </h3>
            <p className="text-xs text-neutral-500">{statusMessage}</p>
          </div>
        )}
      </div>
    </div>
  );
}
