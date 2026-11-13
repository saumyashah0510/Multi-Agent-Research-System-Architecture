/**
 * SocialLoginButtons Component
 *
 * Assignee Task (Issue FE-12):
 * - Wire 'Continue with Google' button using Google Identity Services (or OAuth redirect).
 * - Wire 'Continue with GitHub' button redirecting to GitHub authorization endpoint.
 */

import { FcGoogle } from "react-icons/fc";
import { FaGithub } from "react-icons/fa";

export interface SocialLoginButtonsProps {
  onSuccess?: () => void;
  onError?: (err: string) => void;
}

export default function SocialLoginButtons({ onError }: SocialLoginButtonsProps) {
  const handleGoogleLogin = () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) {
      if (onError) onError("Google Client ID is not configured in .env (VITE_GOOGLE_CLIENT_ID)");
      return;
    }
    const redirectUri = encodeURIComponent(`${window.location.origin}/auth/callback`);
    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=openid%20email%20profile&prompt=select_account`;
    window.location.href = googleAuthUrl;
  };

  const handleGitHubLogin = () => {
    const clientId = import.meta.env.VITE_GITHUB_CLIENT_ID;
    if (!clientId) {
      if (onError) onError("GitHub Client ID is not configured in .env (VITE_GITHUB_CLIENT_ID)");
      return;
    }
    const redirectUri = encodeURIComponent(`${window.location.origin}/auth/callback`);
    const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=user:email`;
    window.location.href = githubAuthUrl;
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      <button
        type="button"
        onClick={handleGoogleLogin}
        className="flex items-center justify-center gap-2 py-2 px-3 border border-neutral-300 rounded-xl text-xs font-semibold text-neutral-800 bg-white hover:bg-neutral-50 transition cursor-pointer shadow-xs"
      >
        <FcGoogle className="w-4 h-4 shrink-0 text-base" />
        <span>Google</span>
      </button>

      <button
        type="button"
        onClick={handleGitHubLogin}
        className="flex items-center justify-center gap-2 py-2 px-3 border border-neutral-300 rounded-xl text-xs font-semibold text-neutral-800 bg-white hover:bg-neutral-50 transition cursor-pointer shadow-xs"
      >
        <FaGithub className="w-4 h-4 shrink-0 text-neutral-900 text-base" />
        <span>GitHub</span>
      </button>
    </div>
  );
}
