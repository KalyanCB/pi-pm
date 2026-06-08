import { create } from 'zustand';
import type { AuthUserPayload, TokenResponse, UserPortfolio } from '@pipm/types';
import { AUTH_BYPASS_ENABLED } from '../auth/authBypass';
import { clearSessionStorage, loadSession, saveSession } from '../storage/sessionStorage';

export type Role = 'owner' | 'viewer' | 'ops_admin' | 'admin';

export interface UserProfile {
  id: string;
  email: string;
  displayName: string;
}

type AuthStatus = 'bootstrapping' | 'authenticated' | 'unauthenticated';

interface AuthState {
  status: AuthStatus;
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: string | null;
  user: UserProfile | null;
  roles: Role[];
  portfolios: UserPortfolio[];
  activePortfolioId: string | null;
  applyTokenResponse: (response: TokenResponse) => void;
  setProfile: (profile: {
    user: UserProfile;
    roles: Role[];
    portfolios: UserPortfolio[];
    portfolioId: string | null;
  }) => void;
  setActivePortfolio: (portfolioId: string) => void;
  clearSession: () => void;
  hasRole: (role: Role) => boolean;
  getPortfolioId: () => string | null;
  isTokenExpired: () => boolean;
  persistSession: () => Promise<void>;
  restoreSession: () => Promise<boolean>;
}

export function mapRoles(roles: string[]): Role[] {
  return roles
    .map((r) => r.toLowerCase().replace(/-/g, '_') as Role)
    .filter((r): r is Role => ['owner', 'viewer', 'ops_admin', 'admin'].includes(r));
}

function toUserProfile(payload: AuthUserPayload): UserProfile {
  return {
    id: payload.id,
    email: payload.email,
    displayName: payload.display_name,
  };
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: AUTH_BYPASS_ENABLED ? 'authenticated' : 'bootstrapping',
  accessToken: null,
  refreshToken: null,
  expiresAt: null,
  user: AUTH_BYPASS_ENABLED ? { id: 'dev', email: 'dev@pipm.local', displayName: 'Dev User' } : null,
  roles: AUTH_BYPASS_ENABLED ? ['owner'] : [],
  portfolios: [],
  activePortfolioId: null,

  applyTokenResponse: (response) => {
    const roles = mapRoles(response.user.roles);
    const portfolioId = response.user.portfolio_id;
    set({
      status: 'authenticated',
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      expiresAt: response.expires_at,
      user: toUserProfile(response.user),
      roles,
      activePortfolioId: get().activePortfolioId ?? portfolioId,
    });
    void get().persistSession();
  },

  setProfile: ({ user, roles, portfolios, portfolioId }) => {
    const active =
      get().activePortfolioId ??
      portfolioId ??
      (portfolios.length === 1 ? (portfolios[0]?.portfolio_id ?? null) : null);
    set({
      user,
      roles,
      portfolios,
      activePortfolioId: active,
      status: 'authenticated',
    });
    void get().persistSession();
  },

  setActivePortfolio: (portfolioId) => {
    set({ activePortfolioId: portfolioId });
    void get().persistSession();
  },

  clearSession: () => {
    void clearSessionStorage();
    set({
      status: 'unauthenticated',
      accessToken: null,
      refreshToken: null,
      expiresAt: null,
      user: null,
      roles: [],
      portfolios: [],
      activePortfolioId: null,
    });
  },

  hasRole: (role) => get().roles.includes(role),

  getPortfolioId: () => get().activePortfolioId,

  isTokenExpired: () => {
    const { expiresAt } = get();
    if (!expiresAt) return true;
    return new Date(expiresAt).getTime() <= Date.now() + 60_000;
  },

  persistSession: async () => {
    const state = get();
    if (!state.accessToken || !state.refreshToken || !state.expiresAt || !state.user) return;
    const session = {
      accessToken: state.accessToken,
      refreshToken: state.refreshToken,
      expiresAt: state.expiresAt,
      user: {
        id: state.user.id,
        email: state.user.email,
        display_name: state.user.displayName,
        roles: state.roles,
        portfolio_id: state.activePortfolioId,
      },
      activePortfolioId: state.activePortfolioId,
    };
    await saveSession(session);
  },

  restoreSession: async () => {
    if (AUTH_BYPASS_ENABLED) {
      set({ status: 'authenticated' });
      return true;
    }
    const stored = await loadSession();
    if (!stored) {
      set({ status: 'unauthenticated' });
      return false;
    }
    set({
      accessToken: stored.accessToken,
      refreshToken: stored.refreshToken,
      expiresAt: stored.expiresAt,
      user: toUserProfile(stored.user),
      roles: mapRoles(stored.user.roles),
      activePortfolioId: stored.activePortfolioId ?? stored.user.portfolio_id,
      status: 'authenticated',
    });
    return true;
  },
}));
