import React, { createContext, useCallback, useContext, useEffect, useRef } from 'react';
import { createPipmApi } from '@pipm/api';
import type { LoginRequest } from '@pipm/types';
import { mapRoles, useAuthStore } from '../stores/authStore';
import { AUTH_BYPASS_ENABLED } from './authBypass';
import { refreshAccessToken } from './refreshAccessToken';

interface AuthContextValue {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export interface AuthProviderProps {
  children: React.ReactNode;
  apiBaseUrl: string;
}

export function AuthProvider({ children, apiBaseUrl }: AuthProviderProps) {
  const refreshInFlight = useRef<Promise<boolean> | null>(null);

  const refreshToken = useAuthStore((s) => s.refreshToken);
  const applyTokenResponse = useAuthStore((s) => s.applyTokenResponse);
  const setProfile = useAuthStore((s) => s.setProfile);
  const clearSession = useAuthStore((s) => s.clearSession);
  const restoreSession = useAuthStore((s) => s.restoreSession);
  const isTokenExpired = useAuthStore((s) => s.isTokenExpired);

  const createAuthApi = useCallback(() => {
    return createPipmApi({
      baseUrl: apiBaseUrl,
      getAccessToken: () => useAuthStore.getState().accessToken,
      getPortfolioId: () => useAuthStore.getState().getPortfolioId(),
    });
  }, [apiBaseUrl]);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    if (refreshInFlight.current) return refreshInFlight.current;
    const run = refreshAccessToken(apiBaseUrl).finally(() => {
      refreshInFlight.current = null;
    });
    refreshInFlight.current = run;
    return run;
  }, [apiBaseUrl]);

  const loadProfile = useCallback(async () => {
    const api = createAuthApi();
    const profile = await api.auth.me();
    setProfile({
      user: {
        id: profile.id,
        email: profile.email,
        displayName: profile.display_name,
      },
      roles: mapRoles(profile.roles),
      portfolios: profile.portfolios ?? [],
      portfolioId: profile.portfolio_id,
    });
  }, [createAuthApi, setProfile]);

  useEffect(() => {
    if (AUTH_BYPASS_ENABLED) return;

    let cancelled = false;

    async function bootstrap() {
      const restored = await restoreSession();
      if (cancelled) return;

      if (!restored) {
        return;
      }

      try {
        if (isTokenExpired()) {
          const ok = await refreshSession();
          if (!ok || cancelled) {
            return;
          }
        }
        await loadProfile();
      } catch {
        clearSession();
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [restoreSession, isTokenExpired, refreshSession, loadProfile, clearSession]);

  const login = useCallback(
    async (credentials: LoginRequest) => {
      const api = createAuthApi();
      const response = await api.auth.login(credentials);
      applyTokenResponse(response);
      await loadProfile();
    },
    [createAuthApi, applyTokenResponse, loadProfile],
  );

  const logout = useCallback(async () => {
    const token = refreshToken;
    clearSession();
    if (token) {
      try {
        const api = createAuthApi();
        await api.auth.logout({ refresh_token: token });
      } catch {
        // Session cleared locally regardless
      }
    }
  }, [refreshToken, clearSession, createAuthApi]);

  return (
    <AuthContext.Provider value={{ login, logout, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}

