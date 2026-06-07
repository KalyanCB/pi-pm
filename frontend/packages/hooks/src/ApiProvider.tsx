import React, { createContext, useContext, useMemo } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createPipmApi, type PipmApi } from '@pipm/api';
import { createQueryClient } from './queryClient';
import { AuthProvider } from './auth/AuthProvider';
import { refreshAccessToken } from './auth/refreshAccessToken';
import { useAuthStore } from './stores/authStore';

const ApiContext = createContext<PipmApi | null>(null);

const queryClient = createQueryClient();

export interface AppProvidersProps {
  children: React.ReactNode;
  apiBaseUrl?: string;
}

export function AppProviders({
  children,
  apiBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1',
}: AppProvidersProps) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const activePortfolioId = useAuthStore((s) => s.activePortfolioId);

  const api = useMemo(
    () =>
      createPipmApi({
        baseUrl: apiBaseUrl,
        getAccessToken: () => useAuthStore.getState().accessToken,
        getPortfolioId: () => useAuthStore.getState().getPortfolioId(),
        onUnauthorized: () => refreshAccessToken(apiBaseUrl),
      }),
    [apiBaseUrl, accessToken, activePortfolioId],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider apiBaseUrl={apiBaseUrl}>
        <ApiContext.Provider value={api}>{children}</ApiContext.Provider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export function useApi(): PipmApi {
  const ctx = useContext(ApiContext);
  if (!ctx) {
    throw new Error('useApi must be used within AppProviders');
  }
  return ctx;
}

export { queryClient };
