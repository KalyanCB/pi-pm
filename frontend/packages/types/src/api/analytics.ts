export interface TrustMetricsDTO {
  overall_trust_score: number | null;
  calibration?: Record<string, unknown>;
  stability?: Record<string, unknown>;
  reliability?: Record<string, unknown>;
}
