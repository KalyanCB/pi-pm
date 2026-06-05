import type { ReconciliationStatus, RiskLevel } from '../enums';
import type { RiskAlert } from './common';

export interface PortfolioDashboardResponse {
  nav: number | null;
  today_change_pct: number | null;
  alpha_pct: number | null;
  cash_pct: number | null;
  active_positions: number;
  pending_exits: number;
  risk_level: RiskLevel;
  risk_alerts: RiskAlert[];
  reconciliation_status: ReconciliationStatus | null;
}

export interface PortfolioPosition {
  id: string;
  symbol: string | null;
  quantity: number;
  avg_cost: number;
  entry_price: number | null;
  entry_date: string | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  weight_pct: number | null;
  conviction_band: string | null;
  strategy_name: string | null;
  sector: string | null;
  position_status: 'OPEN' | 'CLOSED';
}

export interface ExitRecommendation {
  id: string;
  symbol: string | null;
  status: string;
  urgency: string;
  triggers: string[];
  trigger_details: Record<string, unknown>;
  current_rank: number | null;
  days_held: number | null;
  unrealized_pnl_pct: number | null;
  as_of_date: string;
}
