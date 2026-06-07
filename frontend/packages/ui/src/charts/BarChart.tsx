import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface BarChartItem {
  label: string;
  value: number | null;
}

export interface BarChartProps {
  items: BarChartItem[];
  maxBars?: number;
  emptyLabel?: string;
}

export function BarChart({
  items,
  maxBars = 6,
  emptyLabel = 'No data',
}: BarChartProps) {
  const theme = useTheme();
  const visible = items.slice(0, maxBars);
  const values = visible.map((i) => Math.abs(i.value ?? 0));
  const max = Math.max(...values, 1);

  if (visible.length === 0) {
    return <Text style={[styles.empty, { color: theme.colors.textMuted }]}>{emptyLabel}</Text>;
  }

  return (
    <View style={styles.container}>
      {visible.map((item) => {
        const v = item.value ?? 0;
        const widthPct = `${(Math.abs(v) / max) * 100}%`;
        const color = v >= 0 ? theme.colors.positive : theme.colors.negative;
        return (
          <View key={item.label} style={styles.row}>
            <Text style={[styles.label, { color: theme.colors.textSecondary }]} numberOfLines={1}>
              {item.label}
            </Text>
            <View style={[styles.track, { backgroundColor: theme.colors.borderSubtle }]}>
              <View style={[styles.bar, { width: widthPct as `${number}%`, backgroundColor: color }]} />
            </View>
            <Text style={[styles.value, { color: theme.colors.textMono }]}>
              {v !== null ? `${v.toFixed(1)}%` : '—'}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  label: {
    width: 72,
    fontSize: 11,
  },
  track: {
    flex: 1,
    height: 8,
    borderRadius: 2,
    overflow: 'hidden',
  },
  bar: {
    height: '100%',
    borderRadius: 2,
  },
  value: {
    width: 48,
    fontSize: 10,
    textAlign: 'right',
    fontFamily: 'monospace',
  },
  empty: {
    fontSize: 11,
    padding: 12,
  },
});
