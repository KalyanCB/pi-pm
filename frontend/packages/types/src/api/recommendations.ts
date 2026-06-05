import type { Action, ConvictionBand } from '../enums';

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
}

export interface ApproveRequest {
  approval_type?: string;
  decision: string;
  actor_id?: string;
  note?: string | null;
  idempotency_key?: string | null;
}
