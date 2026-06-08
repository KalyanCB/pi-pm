import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { PortfolioPosition } from '@pipm/types';

export interface PositionPnlCardProps {
  positions: PortfolioPosition[];
  title?: string;
}

function formatINR(value: number): string {
  const sign = value < 0 ? '-' : '';
  return `${sign}₹${Math.abs(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

/**
 * Unrealized P&L by position — diverging bars (winners right/green,
 * losers left/red), sorted by P&L. Surfaces what drives the open book.
 */
export function PositionPnlCard({
  positions,
  title = 'UNREALIZED P&L BY POSITION',
}: PositionPnlCardProps) {
  const theme = useTheme();

  const { rows, total, winners, losers, maxAbs, openCount } = useMemo(() => {
    const openAll = positions.filter((p) => p.position_status === 'OPEN');
    const open = openAll
      .filter((p) => p.unrealized_pnl != null)
      .map((p) => ({ label: p.symbol ?? '—', pnl: p.unrealized_pnl ?? 0 }))
      .sort((a, b) => b.pnl - a.pnl);

    const total = open.reduce((a, r) => a + r.pnl, 0);
    const winners = open.filter((r) => r.pnl > 0).length;
    const losers = open.filter((r) => r.pnl < 0).length;
    const maxAbs = open.reduce((m, r) => Math.max(m, Math.abs(r.pnl)), 1);

    return { rows: open, total, winners, losers, maxAbs, openCount: openAll.length };
  }, [positions]);

  if (rows.length === 0) {
    return (
      <View style={[styles.card, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
        <Text style={[styles.title, { color: theme.colors.textMuted }]}>{title}</Text>
        <Text style={[styles.empty, { color: theme.colors.textMuted }]}>
          {openCount > 0
            ? `Per-position P&L unavailable for ${openCount} open position${openCount === 1 ? '' : 's'} (no live quote yet)`
            : 'No open positions'}
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.card, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.textMuted }]}>{title}</Text>
        <Text
          style={[
            styles.meta,
            { color: total >= 0 ? theme.colors.positive : theme.colors.negative },
          ]}
        >
          {formatINR(total)} · {winners}▲ {losers}▼
        </Text>
      </View>

      <View style={styles.rows}>
        {rows.map((r) => {
          const pos = r.pnl >= 0;
          const widthPct = `${(Math.abs(r.pnl) / maxAbs) * 100}%`;
          const color = pos ? theme.colors.positive : theme.colors.negative;
          return (
            <View key={r.label} style={styles.row}>
              <Text style={[styles.label, { color: theme.colors.textSecondary }]} numberOfLines={1}>
                {r.label}
              </Text>
              <View style={styles.diverge}>
                {/* left half (losers) */}
                <View style={styles.half}>
                  {!pos && (
                    <View style={[styles.bar, styles.barLeft, { width: widthPct as `${number}%`, backgroundColor: color }]} />
                  )}
                </View>
                <View style={[styles.axis, { backgroundColor: theme.colors.border }]} />
                {/* right half (winners) */}
                <View style={styles.half}>
                  {pos && (
                    <View style={[styles.bar, styles.barRight, { width: widthPct as `${number}%`, backgroundColor: color }]} />
                  )}
                </View>
              </View>
              <Text style={[styles.value, { color }]}>{formatINR(r.pnl)}</Text>
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
  diverge: { flex: 1, flexDirection: 'row', alignItems: 'center', height: 10 },
  half: { flex: 1, height: '100%', justifyContent: 'center' },
  axis: { width: 1, height: '100%' },
  bar: { height: '100%', borderRadius: 2 },
  barLeft: { alignSelf: 'flex-end' },
  barRight: { alignSelf: 'flex-start' },
  value: { width: 84, fontSize: 10, textAlign: 'right', fontFamily: 'monospace' },
  empty: { fontSize: 11, paddingVertical: 8 },
});
