export function formatTrendRegime(trend: string | undefined): string {
  if (trend === 'BULL') return 'Bull';
  if (trend === 'BEAR') return 'Bear';
  return trend ?? '—';
}

export function formatVolRegime(vol: string | undefined): string {
  if (vol === 'LOW_VOL') return 'Low Volatility';
  if (vol === 'HIGH_VOL') return 'High Volatility';
  return vol ?? '—';
}
