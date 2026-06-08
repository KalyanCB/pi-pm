import type { TrustMetricsDTO } from './analytics';

export interface NavHistoryPoint {
  as_of_date: string;
  total_equity: number;
  cash_balance: number;
  market_value: number;
  unrealized_pnl: number;
  open_positions: number;
  cash_pct: number;
  day_return_pct: number | null;
  alpha_pct: number | null;
  regime_label: string | null;
}

export interface PilotHealthDashboard {
  as_of_date: string;
  health: Record<string, unknown>;
  reconciliation: Record<string, unknown> | null;
  analytics_gate_open: boolean;
  analytics_gate_reason: string | null;
  risk_level: string;
  alerts: Array<{ code: string; level: string; message: string }>;
}

export interface TrustTrendPoint {
  week_ending: string;
  overall_trust_score?: number | null;
  calibration_ok?: boolean | null;
  stability_score?: number | null;
  reliability_rate?: number | null;
}

export interface TrustDashboard {
  window: { from: string; to: string };
  trust: TrustMetricsDTO;
  trend_weekly: TrustTrendPoint[];
  note: string | null;
}

export interface RecommendationPilotToday {
  runs?: number;
  actions?: Record<string, number>;
  buy_count?: number;
  watch_count?: number;
  exit_count?: number;
  hold_count?: number;
  reject_count?: number;
  total?: number;
}

export interface RecommendationPilotDashboard {
  as_of_date: string;
  today: RecommendationPilotToday;
  summary?: Record<string, unknown>;
}
