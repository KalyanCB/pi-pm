export interface RegimeCurrent {
  as_of_date: string;
  benchmark_symbol: string;
  trend_regime: 'BULL' | 'BEAR' | string;
  vol_regime: 'LOW_VOL' | 'HIGH_VOL' | string;
  regime_label: string;
  recorded_at: string;
}
