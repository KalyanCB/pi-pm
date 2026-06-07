import type { Action, ConvictionBand } from '../enums';

export interface RecommendationApprovalRead {
  approval_type: string;
  decision: string;
  decided_at: string;
  actor_id: string;
}

export interface RecommendationTradeRead {
  side: string;
  fill_price: number;
  fill_quantity: number;
  status: string;
  filled_at: string | null;
}

export interface RecommendationPositionRead {
  id: string;
  symbol: string | null;
  quantity: number;
  avg_cost: number;
  entry_price: number | null;
  entry_date: string | null;
  exit_price: number | null;
  exit_date: string | null;
  market_value: number | null;
  unrealized_pnl: number | null;
  realized_pnl: number | null;
  weight_pct: number | null;
  position_status: 'OPEN' | 'CLOSED' | string;
  strategy_name: string | null;
  conviction_band: string | null;
  sector: string | null;
}

export interface RecommendationOutcomeRead {
  outcome_status: string;
  entry_date: string;
  exit_date: string | null;
  pnl_pct: number | null;
  days_held: number | null;
  exit_reason: string | null;
}

export interface RecommendationExecutionContext {
  approvals: RecommendationApprovalRead[];
  trades: RecommendationTradeRead[];
  position: RecommendationPositionRead | null;
  outcome: RecommendationOutcomeRead | null;
}

export interface RecommendationResultRead {
  id: string;
  stock_id: string;
  rank: number | null;
  composite_score: number | null;
  action: Action;
  lifecycle_state: string | null;
  conviction_score: number;
  conviction_band: ConvictionBand;
  conviction_components: Record<string, unknown>;
  reason_codes: string[];
  recommendation_run_id: string;
  portfolio_position_id?: string | null;
}

export interface DailyRecommendationsRead {
  as_of_date: string;
  strategies: DailyStrategyResults[];
  total_results: number;
  buy_count: number;
  watch_count: number;
}

export interface DailyStrategyResults {
  strategy_name: string;
  as_of_date: string;
  recommendation_run_id: string;
  results: RecommendationResultRead[];
  execution_context?: Record<string, RecommendationExecutionContext>;
}

export interface RecommendationDatesRead {
  dates: string[];
  latest_date: string | null;
}

export interface ApproveRequest {
  approval_type?: string;
  decision: string;
  actor_id?: string;
  note?: string | null;
  idempotency_key?: string | null;
}
