export interface CommitteeAdvisoryOverlay {
  cro_advisory_action: string | null;
  high_concern: boolean;
  high_concern_committees: string[];
  committee_actions: Record<string, string>;
  display_names: Record<string, string>;
  note?: string;
}

export interface CommitteePacket {
  packet_id: string;
  symbol: string;
  packet_hash: string;
  packet_version: string;
  payload: {
    recommendation?: {
      action: string;
      conviction_score: number;
      conviction_band: string;
      reason_codes: string[];
    };
    committee_advisory?: CommitteeAdvisoryOverlay;
  };
  built_at: string;
}

export interface CommitteeReviewFinding {
  committee_code: string;
  symbol: string;
  findings: string;
  confidence: number | null;
  supporting_evidence: Array<{ ref: string; note?: string }>;
}

export interface CommitteeExplainResponse {
  research_run_id: string;
  status: string;
  committee_reviews: CommitteeReviewFinding[];
}

export interface CommitteeReviewSummary {
  run_id: string;
  status: string;
  as_of_date: string;
  candidates_reviewed: number;
  governance_reports_issued?: number;
  universe_code?: string;
  strategy_name?: string;
}
