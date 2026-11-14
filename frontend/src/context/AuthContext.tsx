/**
 * AuthContext & Provider
 *
 * Assignee Task (Issue FE-11):
 * - Persist JWT token in localStorage under 'scholaris_token'.
 * - Provide login, register, and logout functions.
 * - On initial load, fetch user profile via fetchCurrentUser().
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserProfile } from "../types";
import {
  clearAuthToken,
  fetchCurrentUser,
  getAuthToken,
  loginUser,
  registerUser,
  setAuthToken,
} from "../lib/api";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
  setSession: (token: string, user: UserProfile) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // TODO (Assignee - FE-11): Restore user session if token exists
    const initAuth = async () => {
      const existingToken = getAuthToken();
      if (!existingToken) {
        setIsLoading(false);
        return;
      }
      try {
        const profile = await fetchCurrentUser();
        setUser(profile);
      } catch (err) {
        console.warn("Session restore failed, clearing token:", err);
        clearAuthToken();
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    // TODO (Assignee - FE-11): Call loginUser, set token in storage and state, set user
    setIsLoading(true);
    try {
      const data = await loginUser(email, password);
      setAuthToken(data.access_token);
      setToken(data.access_token);
      setUser(data.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, name?: string) => {
    // TODO (Assignee - FE-11): Call registerUser, set token in storage and state, set user
    setIsLoading(true);
    try {
      const data = await registerUser(email, password, name);
      setAuthToken(data.access_token);
      setToken(data.access_token);
      setUser(data.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    // TODO (Assignee - FE-11): Clear token from storage and state, reset user
    clearAuthToken();
    setToken(null);
    setUser(null);
  };

  const setSession = (newToken: string, newUser: UserProfile) => {
    setAuthToken(newToken);
    setToken(newToken);
    setUser(newUser);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        register,
        logout,
        setSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
