import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { TrustScoreCardProps } from '@pipm/types';

export function TrustScoreCard({ score, showBreakdown = false }: TrustScoreCardProps) {
  const theme = useTheme();
  const display = score !== null ? `${(score * 100).toFixed(1)}%` : '—';
  const barWidth = score !== null ? `${Math.round(score * 100)}%` : '0%';

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.backgroundPanel,
          borderColor: theme.colors.border,
        },
      ]}
    >
      <Text style={[styles.label, { color: theme.colors.textMuted }]}>TRUST SCORE</Text>
      <Text style={[styles.score, { color: theme.colors.accent }]}>{display}</Text>
      <View style={[styles.track, { backgroundColor: theme.colors.borderSubtle }]}>
        <View
          style={[
            styles.fill,
            {
              backgroundColor: theme.colors.accent,
              width: barWidth as `${number}%`,
            },
          ]}
        />
      </View>
      {showBreakdown && (
        <Text style={[styles.note, { color: theme.colors.textMuted }]}>
          Calibration · Stability · Reliability
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 6,
    minWidth: 140,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
  },
  score: {
    fontSize: 24,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  track: {
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 2,
  },
  note: {
    fontSize: 10,
    marginTop: 4,
  },
});
