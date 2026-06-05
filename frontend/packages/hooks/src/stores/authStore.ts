import { create } from 'zustand';

export type Role = 'owner' | 'viewer' | 'ops_admin';

export interface UserProfile {
  id: string;
  email: string;
  displayName: string;
}

interface AuthState {
  status: 'unknown' | 'authenticated' | 'unauthenticated';
  accessToken: string | null;
  user: UserProfile | null;
  roles: Role[];
  setSession: (session: {
    accessToken: string;
    user: UserProfile;
    roles: Role[];
  }) => void;
  clearSession: () => void;
  hasRole: (role: Role) => boolean;
}

const DEV_BYPASS =
  typeof process !== 'undefined' && process.env?.EXPO_PUBLIC_AUTH_BYPASS === 'true';

export const useAuthStore = create<AuthState>((set, get) => ({
  status: DEV_BYPASS ? 'authenticated' : 'authenticated',
  accessToken: DEV_BYPASS ? 'dev-token' : null,
  user: DEV_BYPASS
    ? { id: 'dev', email: 'owner@pipm.local', displayName: 'Owner' }
    : { id: 'local', email: 'owner@pipm.local', displayName: 'Owner' },
  roles: ['owner'],
  setSession: (session) =>
    set({
      status: 'authenticated',
      accessToken: session.accessToken,
      user: session.user,
      roles: session.roles,
    }),
  clearSession: () =>
    set({
      status: 'unauthenticated',
      accessToken: null,
      user: null,
      roles: [],
    }),
  hasRole: (role) => get().roles.includes(role),
}));
