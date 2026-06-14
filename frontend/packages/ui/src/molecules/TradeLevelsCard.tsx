import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface TradeLevelsCardProps {
  entryLow?: number | null;
  entryHigh?: number | null;
  stopAdvisory?: number | null;
  stopCritical?: number | null;
  referenceClose?: number | null;
  atrPct?: number | null;
  /** "actionable" (BUY) | "indicative" (WATCH). */
  basis?: 'actionable' | 'indicative' | null;
}

function inr(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—';
  return `₹${v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * ADR-034: deterministic entry range + stop-loss range for a recommendation.
 * Actionable (BUY) vs indicative (WATCH) is made explicit; indicative is a plan,
 * never an order.
 */
export function TradeLevelsCard({
  entryLow,
  entryHigh,
  stopAdvisory,
  stopCritical,
  referenceClose,
  atrPct,
  basis = 'actionable',
}: TradeLevelsCardProps) {
  const theme = useTheme();

  // Nothing to show if no levels were computed (e.g. REJECT, or no market data).
  if (entryLow == null && entryHigh == null && stopAdvisory == null && stopCritical == null) {
    return null;
  }

  const indicative = basis === 'indicative';
  const accent = indicative ? theme.colors.warning : theme.colors.positive;

  return (
    <View
      style={[
        styles.card,
        { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.textMuted }]}>TRADE LEVELS</Text>
        <View style={[styles.chip, { borderColor: accent }]}>
          <Text style={[styles.chipText, { color: accent }]}>
            {indicative ? 'INDICATIVE' : 'ACTIONABLE'}
          </Text>
        </View>
      </View>

      <View style={styles.row}>
        <Text style={[styles.label, { color: theme.colors.textSecondary }]}>Entry range</Text>
        <Text style={[styles.value, { color: theme.colors.textMono }]}>
          {inr(entryLow)} – {inr(entryHigh)}
        </Text>
      </View>

      <View style={styles.row}>
        <Text style={[styles.label, { color: theme.colors.textSecondary }]}>Stop (advisory)</Text>
        <Text style={[styles.value, { color: theme.colors.textMono }]}>{inr(stopAdvisory)}</Text>
      </View>

      <View style={styles.row}>
        <Text style={[styles.label, { color: theme.colors.textSecondary }]}>Stop (critical)</Text>
        <Text style={[styles.value, { color: theme.colors.negative }]}>{inr(stopCritical)}</Text>
      </View>

      <Text style={[styles.meta, { color: theme.colors.textMuted }]}>
        {referenceClose != null ? `ref close ${inr(referenceClose)}` : ''}
        {atrPct != null ? ` · ATR ${atrPct.toFixed(2)}%` : ''}
        {indicative ? ' · plan only — not an order' : ''}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderRadius: 6, padding: 14, gap: 8 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  chip: { borderWidth: 1, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  chipText: { fontSize: 9, fontWeight: '700', letterSpacing: 0.5 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { fontSize: 12 },
  value: { fontSize: 13, fontFamily: 'monospace', fontWeight: '600' },
  meta: { fontSize: 10, fontFamily: 'monospace', marginTop: 2 },
});
