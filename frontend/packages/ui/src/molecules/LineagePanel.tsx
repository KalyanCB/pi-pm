import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { LineageSummary } from '@pipm/types';

export interface LineagePanelProps {
  lineage: LineageSummary;
}

function LineageGroup({ label, ids }: { label: string; ids: string[] }) {
  const theme = useTheme();
  if (ids.length === 0) return null;
  return (
    <View style={styles.group}>
      <Text style={[styles.label, { color: theme.colors.textMuted }]}>{label}</Text>
      {ids.slice(0, 3).map((id) => (
        <Text key={id} style={[styles.id, { color: theme.colors.textSecondary }]} numberOfLines={1}>
          {id}
        </Text>
      ))}
      {ids.length > 3 && (
        <Text style={[styles.more, { color: theme.colors.textMuted }]}>+{ids.length - 3} more</Text>
      )}
    </View>
  );
}

export function LineagePanel({ lineage }: LineagePanelProps) {
  const theme = useTheme();
  const hasData =
    lineage.recommendation_run_ids.length > 0 ||
    lineage.recommendation_ids.length > 0 ||
    lineage.portfolio_position_ids.length > 0 ||
    lineage.committee_review_ids.length > 0;

  if (!hasData) return null;

  return (
    <View style={[styles.panel, { borderColor: theme.colors.border, backgroundColor: theme.colors.background }]}>
      <Text style={[styles.title, { color: theme.colors.textMuted }]}>LINEAGE</Text>
      <LineageGroup label="Recommendation runs" ids={lineage.recommendation_run_ids} />
      <LineageGroup label="Recommendations" ids={lineage.recommendation_ids} />
      <LineageGroup label="Positions" ids={lineage.portfolio_position_ids} />
      <LineageGroup label="Committee reviews" ids={lineage.committee_review_ids} />
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    borderWidth: 1,
    borderRadius: 4,
    padding: 8,
    gap: 6,
    marginTop: 8,
  },
  title: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  group: {
    gap: 2,
  },
  label: {
    fontSize: 10,
    textTransform: 'uppercase',
  },
  id: {
    fontSize: 10,
    fontFamily: 'monospace',
  },
  more: {
    fontSize: 10,
  },
});
