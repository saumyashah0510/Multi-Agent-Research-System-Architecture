/**
 * SocialLoginButtons Component
 *
 * Assignee Task (Issue FE-12):
 * - Wire 'Continue with Google' button using Google Identity Services (or OAuth redirect).
 * - Wire 'Continue with GitHub' button redirecting to GitHub authorization endpoint.
 */

export interface SocialLoginButtonsProps {
  onSuccess?: () => void;
  onError?: (err: string) => void;
}

export default function SocialLoginButtons({ onError }: SocialLoginButtonsProps) {
  const handleGoogleLogin = () => {
    // TODO (Assignee - FE-12):
    // 1. Read VITE_GOOGLE_CLIENT_ID from import.meta.env
    // 2. Open Google OAuth prompt or redirect to Google OAuth URL:
    //    https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=.../auth/callback&response_type=code&scope=openid%20email%20profile
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
    // TODO (Assignee - FE-12):
    // 1. Read VITE_GITHUB_CLIENT_ID from import.meta.env
    // 2. Redirect to GitHub OAuth URL:
    //    https://github.com/login/oauth/authorize?client_id=...&redirect_uri=.../auth/callback&scope=user:email
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
        className="flex items-center justify-center gap-2 py-2 px-3 border border-neutral-200 rounded-xl text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition cursor-pointer"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.05h3.9c2.28-2.1 3.64-5.2 3.64-9.15z"
          />
          <path
            fill="#34A853"
            d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.9-3.05c-1.08.72-2.45 1.16-4.03 1.16-3.1 0-5.74-2.1-6.68-4.94H1.26v3.15C3.26 21.36 7.35 24 12 24z"
          />
          <path
            fill="#FBBC05"
            d="M5.32 14.26a7.2 7.2 0 010-4.52V6.59H1.26a11.97 11.97 0 000 10.82l4.06-3.15z"
          />
          <path
            fill="#EA4335"
            d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.26 6.59l4.06 3.15c.94-2.84 3.58-4.99 6.68-4.99z"
          />
        </svg>
        Google
      </button>

      <button
        type="button"
        onClick={handleGitHubLogin}
        className="flex items-center justify-center gap-2 py-2 px-3 border border-neutral-200 rounded-xl text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition cursor-pointer"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path
            fillRule="evenodd"
            d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            clipRule="evenodd"
          />
        </svg>
        GitHub
      </button>
    </div>
  );
}
