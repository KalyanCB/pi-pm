import { createPipmApi } from '@pipm/api';
import { useAuthStore } from '../stores/authStore';

export async function refreshAccessToken(apiBaseUrl: string): Promise<boolean> {
  const { refreshToken, applyTokenResponse, clearSession } = useAuthStore.getState();
  if (!refreshToken) {
    clearSession();
    return false;
  }
  try {
    const api = createPipmApi({
      baseUrl: apiBaseUrl,
      getAccessToken: () => useAuthStore.getState().accessToken,
      getPortfolioId: () => useAuthStore.getState().getPortfolioId(),
    });
    const response = await api.auth.refresh({ refresh_token: refreshToken });
    applyTokenResponse(response);
    return true;
  } catch {
    clearSession();
    return false;
  }
}
