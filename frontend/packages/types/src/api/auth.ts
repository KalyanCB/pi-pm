export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface LogoutRequest {
  refresh_token: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_at: string;
  user: AuthUserPayload;
}

export interface AuthUserPayload {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  portfolio_id: string | null;
}

export interface UserPortfolio {
  portfolio_id: string;
  role: string;
  name: string | null;
}

export interface UserProfileResponse {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  portfolio_id: string | null;
  preferences?: {
    timezone: string;
    locale: string;
    settings: Record<string, unknown>;
  };
  portfolios: UserPortfolio[];
}

export interface StoredSession {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  user: AuthUserPayload;
  activePortfolioId: string | null;
}
