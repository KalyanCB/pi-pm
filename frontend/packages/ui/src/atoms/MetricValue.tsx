import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface MetricValueProps {
  value: number | string | null;
  format?: 'currency' | 'percent' | 'number' | 'integer';
  colorize?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

function formatValue(
  value: number | string | null,
  format: MetricValueProps['format'],
): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  switch (format) {
    case 'currency':
      return `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
    case 'percent':
      return `${value.toFixed(2)}%`;
    case 'integer':
      return String(Math.round(value));
    default:
      return value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  }
}

export function MetricValue({
  value,
  format = 'number',
  colorize = false,
  size = 'md',
}: MetricValueProps) {
  const theme = useTheme();
  const display = formatValue(value, format);
  let color: string = theme.colors.textMono;

  if (colorize && typeof value === 'number') {
    if (value > 0) color = theme.colors.positive;
    else if (value < 0) color = theme.colors.negative;
  }

  const fontSize =
    size === 'lg' ? theme.typography.fontSize.xxl : size === 'sm' ? theme.typography.fontSize.sm : theme.typography.fontSize.lg;

  return (
    <Text style={[styles.mono, { color, fontSize }]} accessibilityLabel={display}>
      {display}
    </Text>
  );
}

const styles = StyleSheet.create({
  mono: {
    fontFamily: 'monospace',
    fontWeight: '600',
  },
});
