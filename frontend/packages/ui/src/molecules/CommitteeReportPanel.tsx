import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface CommitteeReportEntry {
  symbol: string;
  summary: string;
  narrative: string;
  confidence: number | null;
}

export interface CommitteeReportPanelProps {
  reports: CommitteeReportEntry[];
}

export function CommitteeReportPanel({ reports }: CommitteeReportPanelProps) {
  const theme = useTheme();
  if (reports.length === 0) return null;

  return (
    <View style={styles.panel}>
      <Text style={[styles.title, { color: theme.colors.textMuted }]}>COMMITTEE REPORT</Text>
      {reports.map((r) => (
        <View
          key={r.symbol}
          style={[styles.card, { backgroundColor: theme.colors.backgroundElevated, borderColor: theme.colors.border }]}
        >
          <View style={styles.header}>
            <Text style={[styles.symbol, { color: theme.colors.textPrimary }]}>{r.symbol}</Text>
            {r.confidence !== null && (
              <Text style={[styles.conf, { color: theme.colors.textMuted }]}>
                {(r.confidence * 100).toFixed(0)}% conf
              </Text>
            )}
          </View>
          <Text style={[styles.summary, { color: theme.colors.textSecondary }]}>{r.summary}</Text>
          <Text style={[styles.narrative, { color: theme.colors.textPrimary }]}>{r.narrative}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    gap: 10,
  },
  title: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  card: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 6,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  symbol: {
    fontSize: 14,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  conf: {
    fontSize: 10,
    fontFamily: 'monospace',
  },
  summary: {
    fontSize: 12,
    fontWeight: '600',
  },
  narrative: {
    fontSize: 13,
    lineHeight: 19,
  },
});
