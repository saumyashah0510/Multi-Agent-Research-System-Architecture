/**
 * AuthCallback Page
 *
 * Assignee Task (Issue FE-12):
 * - Parse OAuth query params (code, credential, error).
 * - Invoke authWithGoogle() or authWithGitHub().
 * - Update AuthContext with setSession(access_token, user).
 * - Redirect user to /dashboard.
 */

import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authWithGitHub, authWithGoogle } from "../lib/api";
import scholarisLogo from "../images/Scholaris_logo.png";

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setSession } = useAuth();

  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string>("Authenticating with provider...");

  useEffect(() => {
    const processCallback = async () => {
      // 1. Check for error returned by OAuth provider
      const oauthError = searchParams.get("error_description") || searchParams.get("error");
      if (oauthError) {
        setError(`Authentication denied: ${oauthError}`);
        return;
      }

      const code = searchParams.get("code");
      const credential = searchParams.get("credential");

      if (!code && !credential) {
        setError("Missing authorization parameters. Please try signing in again.");
        return;
      }

      try {
        let authData: any = null;

        // TODO (Assignee - FE-12):
        // 1. Determine whether Google or GitHub returned the response
        // 2. If credential (Google ID token) or code with Google scope:
        if (credential) {
          setStatusMessage("Verifying Google account...");
          authData = await authWithGoogle(credential);
        } else if (code) {
          // Check if GitHub code or Google code
          setStatusMessage("Exchanging authorization code...");
          try {
            // Attempt GitHub code exchange
            authData = await authWithGitHub(code);
          } catch (ghErr) {
            // Fallback attempt with Google code
            authData = await authWithGoogle(undefined, code);
          }
        }

        if (authData && authData.access_token) {
          setSession(authData.access_token, authData.user);
          setStatusMessage("Authentication successful! Redirecting to research dashboard...");
          setTimeout(() => {
            navigate("/dashboard", { replace: true });
          }, 400);
        } else {
          throw new Error("Invalid response received from authentication service.");
        }
      } catch (err: any) {
        console.error("OAuth callback error:", err);
        setError(err.message || "Failed to complete authentication. Please try again.");
      }
    };

    processCallback();
  }, [searchParams, navigate, setSession]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-surface text-neutral-900">
      <div className="w-full max-w-md bg-white/80 backdrop-blur-md rounded-2xl border border-neutral-200/80 shadow-card p-8 text-center">
        <img src={scholarisLogo} alt="Scholaris Logo" className="h-10 mx-auto object-contain mb-4" />

        {error ? (
          <div>
            <div className="p-3 mb-4 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
              {error}
            </div>
            <Link
              to="/login"
              className="inline-block py-2 px-4 rounded-xl bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition"
            >
              Back to Sign In
            </Link>
          </div>
        ) : (
          <div>
            <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h3 className="font-serif-heading text-lg font-semibold text-neutral-900 mb-1">
              Signing you in
            </h3>
            <p className="text-xs text-neutral-500">{statusMessage}</p>
          </div>
        )}
      </div>
    </div>
  );
}
