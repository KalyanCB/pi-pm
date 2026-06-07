import type {
  LoginRequest,
  LogoutRequest,
  RefreshRequest,
  TokenResponse,
  UserProfileResponse,
} from '@pipm/types';
import type { ApiClient } from './client';

export function createAuthApi(client: ApiClient) {
  return {
    login(body: LoginRequest) {
      return client.post<TokenResponse>('/auth/login', body);
    },
    refresh(body: RefreshRequest) {
      return client.post<TokenResponse>('/auth/refresh', body);
    },
    logout(body: LogoutRequest) {
      return client.post<void>('/auth/logout', body);
    },
    me() {
      return client.get<UserProfileResponse>('/auth/me');
    },
  };
}

export type AuthApi = ReturnType<typeof createAuthApi>;
