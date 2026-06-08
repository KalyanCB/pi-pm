import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { PortfolioPosition } from '@pipm/types';
import { DonutChart, type DonutSegment } from '../charts/DonutChart';

export interface ConvictionMixCardProps {
  positions: PortfolioPosition[];
  title?: string;
}

const BAND_ORDER = ['HIGH', 'MEDIUM', 'LOW'] as const;

/**
 * Conviction mix of the open book — share of capital in HIGH / MEDIUM / LOW
 * conviction, weighted by portfolio weight (falls back to market value, then
 * position count). Reads the *quality* of the current book, not just its size.
 */
export function ConvictionMixCard({
  positions,
  title = 'CONVICTION MIX',
}: ConvictionMixCardProps) {
  const theme = useTheme();

  const bandColor: Record<string, string> = {
    HIGH: theme.colors.positive,
    MEDIUM: theme.colors.warning,
    LOW: theme.colors.negative,
    UNRATED: theme.colors.textMuted,
  };

  const { segments, openCount, basis } = useMemo(() => {
    const open = positions.filter((p) => p.position_status === 'OPEN');
    const useWeight = open.some((p) => (p.weight_pct ?? 0) > 0);
    const useValue = !useWeight && open.some((p) => (p.market_value ?? 0) > 0);
    const basis = useWeight ? 'weight' : useValue ? 'value' : 'count';

    const map = new Map<string, number>();
    for (const p of open) {
      const band = (p.conviction_band ?? '').toUpperCase() || 'UNRATED';
      const value = useWeight ? (p.weight_pct ?? 0) : useValue ? (p.market_value ?? 0) : 1;
      if (value > 0) map.set(band, (map.get(band) ?? 0) + value);
    }

    const ordered = [...BAND_ORDER, 'UNRATED'].filter((b) => map.has(b));
    const segments: DonutSegment[] = ordered.map((band) => ({
      label: band.charAt(0) + band.slice(1).toLowerCase(),
      value: map.get(band) ?? 0,
      color: bandColor[band],
    }));

    return { segments, openCount: open.length, basis };
  }, [positions]);

  const basisLabel = basis === 'weight' ? 'by weight' : basis === 'value' ? 'by market value' : 'by count';

  return (
    <View style={[styles.card, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.textMuted }]}>{title}</Text>
        <Text style={[styles.meta, { color: theme.colors.textMuted }]}>
          {openCount} open · {basisLabel}
        </Text>
      </View>
      <DonutChart segments={segments} emptyLabel="No open positions" maxLegend={4} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 6, padding: 14, gap: 12 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 4 },
  title: { fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  meta: { fontSize: 10, fontFamily: 'monospace' },
});
