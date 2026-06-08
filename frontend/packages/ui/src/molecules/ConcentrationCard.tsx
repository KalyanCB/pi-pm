import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { PortfolioPosition } from '@pipm/types';

export interface ConcentrationCardProps {
  positions: PortfolioPosition[];
  /** Per-position weight cap in percent (default 25). */
  capPct?: number;
  title?: string;
}

/**
 * Concentration & cap-compliance card: each open position's weight vs the
 * per-position cap, with breaches flagged and a top-3 concentration read.
 */
export function ConcentrationCard({
  positions,
  capPct = 25,
  title = 'CONCENTRATION VS CAP',
}: ConcentrationCardProps) {
  const theme = useTheme();

  const { rows, top3, breaches, scaleMax } = useMemo(() => {
    const open = positions
      .filter((p) => p.position_status === 'OPEN' && (p.weight_pct ?? 0) > 0)
      .map((p) => ({ label: p.symbol ?? '—', weight: p.weight_pct ?? 0 }))
      .sort((a, b) => b.weight - a.weight);

    const maxWeight = open.reduce((m, r) => Math.max(m, r.weight), 0);
    const scaleMax = Math.max(capPct * 1.1, maxWeight);
    const top3 = open.slice(0, 3).reduce((a, r) => a + r.weight, 0);
    const breaches = open.filter((r) => r.weight > capPct).length;

    return { rows: open, top3, breaches, scaleMax };
  }, [positions, capPct]);

  if (rows.length === 0) {
    return (
      <View style={[styles.card, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
        <Text style={[styles.title, { color: theme.colors.textMuted }]}>{title}</Text>
        <Text style={[styles.empty, { color: theme.colors.textMuted }]}>No open positions</Text>
      </View>
    );
  }

  const capLeft = `${(capPct / scaleMax) * 100}%`;

  return (
    <View style={[styles.card, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.textMuted }]}>{title}</Text>
        <Text style={[styles.meta, { color: breaches > 0 ? theme.colors.negative : theme.colors.textMuted }]}>
          top‑3 {top3.toFixed(1)}% · {breaches > 0 ? `${breaches} over ${capPct}%` : `cap ${capPct}%`}
        </Text>
      </View>

      <View style={styles.rows}>
        {rows.map((r) => {
          const over = r.weight > capPct;
          const barColor = over ? theme.colors.negative : theme.colors.positive;
          return (
            <View key={r.label} style={styles.row}>
              <Text style={[styles.label, { color: theme.colors.textSecondary }]} numberOfLines={1}>
                {r.label}
              </Text>
              <View style={[styles.track, { backgroundColor: theme.colors.borderSubtle }]}>
                <View
                  style={[styles.bar, { width: `${(r.weight / scaleMax) * 100}%` as `${number}%`, backgroundColor: barColor }]}
                />
                {/* cap reference line */}
                <View style={[styles.capLine, { left: capLeft as `${number}%`, backgroundColor: theme.colors.warning }]} />
              </View>
              <Text style={[styles.value, { color: over ? theme.colors.negative : theme.colors.textMono }]}>
                {r.weight.toFixed(1)}%
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 6, padding: 14, gap: 12 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 4 },
  title: { fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  meta: { fontSize: 10, fontFamily: 'monospace' },
  rows: { gap: 8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  label: { width: 84, fontSize: 11 },
  track: { flex: 1, height: 10, borderRadius: 2, overflow: 'hidden', position: 'relative' },
  bar: { height: '100%', borderRadius: 2 },
  capLine: { position: 'absolute', top: 0, bottom: 0, width: 2 },
  value: { width: 52, fontSize: 10, textAlign: 'right', fontFamily: 'monospace' },
  empty: { fontSize: 11, paddingVertical: 8 },
});
