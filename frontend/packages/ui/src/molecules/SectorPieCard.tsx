import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { PortfolioPosition } from '@pipm/types';
import { DonutChart } from '../charts/DonutChart';

export interface SectorPieCardProps {
  positions: PortfolioPosition[];
  title?: string;
}

/**
 * Pie/donut card showing active (OPEN) positions grouped by sector.
 *
 * Weighting preference: portfolio weight % → market value → position count,
 * whichever is available, so the chart stays meaningful even before NAV-based
 * weights are computed.
 */
export function SectorPieCard({
  positions,
  title = 'ACTIVE POSITIONS BY SECTOR',
}: SectorPieCardProps) {
  const theme = useTheme();

  const { segments, openCount, basis } = useMemo(() => {
    const open = positions.filter((p) => p.position_status === 'OPEN');
    const useWeight = open.some((p) => (p.weight_pct ?? 0) > 0);
    const useValue = !useWeight && open.some((p) => (p.market_value ?? 0) > 0);
    const basis = useWeight ? 'weight' : useValue ? 'value' : 'count';

    const map = new Map<string, number>();
    for (const p of open) {
      const sector = p.sector?.trim() || 'Other';
      const value = useWeight
        ? (p.weight_pct ?? 0)
        : useValue
          ? (p.market_value ?? 0)
          : 1;
      if (value > 0) map.set(sector, (map.get(sector) ?? 0) + value);
    }

    const segments = [...map.entries()]
      .map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value);

    return { segments, openCount: open.length, basis };
  }, [positions]);

  const basisLabel =
    basis === 'weight' ? 'by weight' : basis === 'value' ? 'by market value' : 'by count';

  return (
    <View
      style={[
        styles.card,
        { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.textMuted }]}>{title}</Text>
        <Text style={[styles.meta, { color: theme.colors.textMuted }]}>
          {openCount} open · {basisLabel}
        </Text>
      </View>
      <DonutChart segments={segments} emptyLabel="No open positions" maxLegend={10} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 14,
    gap: 12,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 4,
  },
  title: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  meta: {
    fontSize: 10,
    fontFamily: 'monospace',
  },
});
