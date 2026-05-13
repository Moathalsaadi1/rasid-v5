import { useCallback, useEffect, useState } from "react";
import { me } from "../api/client";
import type { CurrentUser, UserRole } from "../types";

const STORAGE_KEY_API = "rasid_api_key";
const STORAGE_KEY_EMAIL = "rasid_user_email";

interface UseSessionReturn {
  apiKey: string;
  user: CurrentUser | null;
  bootstrapping: boolean;
  setSession: (apiKey: string, user: CurrentUser) => void;
  setApiKey: (key: string) => void;       // for rotate flow
  logout: () => void;
  error: string;
  clearError: () => void;
}

// Manages auth state and rehydrates the current user on app load if an
// api key was previously stored. Keeps the auth concerns out of App.tsx.
export function useSession(): UseSessionReturn {
  const [apiKey, setApiKeyState] = useState(
    () => localStorage.getItem(STORAGE_KEY_API) || "",
  );
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [bootstrapping, setBootstrapping] = useState(!!apiKey);
  const [error, setError] = useState("");

  // On first mount (and whenever the apiKey changes), validate it and
  // pull the current user. Failed validation clears the stored key.
  useEffect(() => {
    if (!apiKey) {
      setUser(null);
      setBootstrapping(false);
      return;
    }
    setBootstrapping(true);
    me(apiKey)
      .then((d) => setUser(d.user))
      .catch((e: Error) => {
        setError(e.message);
        localStorage.removeItem(STORAGE_KEY_API);
        setApiKeyState("");
        setUser(null);
      })
      .finally(() => setBootstrapping(false));
  }, [apiKey]);

  const setSession = useCallback((key: string, u: CurrentUser) => {
    localStorage.setItem(STORAGE_KEY_API, key);
    localStorage.setItem(STORAGE_KEY_EMAIL, u.email);
    setApiKeyState(key);
    setUser(u);
    setError("");
  }, []);

  const setApiKey = useCallback((key: string) => {
    localStorage.setItem(STORAGE_KEY_API, key);
    setApiKeyState(key);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY_API);
    localStorage.removeItem(STORAGE_KEY_EMAIL);
    setApiKeyState("");
    setUser(null);
    setError("");
  }, []);

  return {
    apiKey,
    user,
    bootstrapping,
    setSession,
    setApiKey,
    logout,
    error,
    clearError: () => setError(""),
  };
}

// Convenience: returns role helpers based on the current session.
export function useIsAdmin(user: CurrentUser | null): boolean {
  return user?.role === ("admin" as UserRole);
}
