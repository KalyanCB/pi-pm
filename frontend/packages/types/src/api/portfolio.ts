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
  exit_price: number | null;
  exit_date: string | null;
  realized_pnl: number | null;
  exit_reason: string | null;
}

export interface PortfolioSummary {
  total_equity: number;
  deployable_capital: number;
  cash_available: number;
  cash_pct: number;
  market_value: number;
  unrealized_pnl: number;
  active_positions: number;
  regime_posture: string;
  max_positions: number;
  slots_available: number;
  max_buy_per_day: number;
}

export interface AttributionBucket {
  label: string;
  count: number;
  total_return_pct: number | null;
  avg_return_pct: number | null;
  avg_alpha_pct: number | null;
  win_rate: number | null;
  contribution_pct: number | null;
}

export interface AttributionReport {
  by_strategy: AttributionBucket[];
  by_conviction_band: AttributionBucket[];
  by_regime: AttributionBucket[];
  by_sector: AttributionBucket[];
  by_holding_duration: AttributionBucket[];
  by_committee_advisory: AttributionBucket[];
  total_alpha_pct: number | null;
  note: string | null;
}

export interface PerformanceMetrics {
  total_return_pct: number | null;
  cagr_pct: number | null;
  alpha_pct: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate: number | null;
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
