import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { TrustMetricsDTO } from '@pipm/types';

function scoreFrom(
  obj: Record<string, unknown> | undefined,
  dimension: 'calibration' | 'stability' | 'reliability',
): number | null {
  if (!obj) return null;
  const generic = obj.score ?? obj.value ?? obj.overall;
  if (typeof generic === 'number') return generic;

  if (dimension === 'calibration') {
    const rho = obj.rank_correlation;
    if (typeof rho === 'number') return Math.max(0, Math.min(1, (rho + 1) / 2));
    if (obj.is_calibrated === true) return 1;
    if (obj.is_calibrated === false) return 0;
  }
  if (dimension === 'stability' && typeof obj.stability_score === 'number') {
    return obj.stability_score;
  }
  if (dimension === 'reliability' && typeof obj.reliability_rate === 'number') {
    return obj.reliability_rate;
  }
  return null;
}

export interface TrustIndicatorStripProps {
  trust?: TrustMetricsDTO | null;
  compact?: boolean;
}

export function TrustIndicatorStrip({ trust, compact = false }: TrustIndicatorStripProps) {
  const theme = useTheme();
  const items = [
    { key: 'Calibration', score: scoreFrom(trust?.calibration, 'calibration') },
    { key: 'Stability', score: scoreFrom(trust?.stability, 'stability') },
    { key: 'Reliability', score: scoreFrom(trust?.reliability, 'reliability') },
  ];

  return (
    <View style={[styles.strip, compact && styles.compact]}>
      {items.map((item) => (
        <View
          key={item.key}
          style={[styles.pill, { backgroundColor: theme.colors.background, borderColor: theme.colors.border }]}
        >
          <Text style={[styles.pillLabel, { color: theme.colors.textMuted }]}>{item.key}</Text>
          <Text style={[styles.pillValue, { color: theme.colors.accent }]}>
            {item.score !== null ? `${(item.score * 100).toFixed(0)}%` : '—'}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  strip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  compact: {
    gap: 4,
  },
  pill: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    gap: 2,
  },
  pillLabel: {
    fontSize: 9,
    fontWeight: '600',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  pillValue: {
    fontSize: 12,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
});
