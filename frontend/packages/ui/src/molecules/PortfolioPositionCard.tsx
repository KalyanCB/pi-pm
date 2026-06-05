import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { PortfolioPositionCardProps } from '@pipm/types';
import { MetricValue } from '../atoms/MetricValue';
import { Badge } from '../atoms/Badge';

export function PortfolioPositionCard({
  symbol,
  quantity,
  avgCost,
  marketValue,
  unrealizedPnl,
  weightPct,
  convictionBand,
  sector,
  onPress,
}: PortfolioPositionCardProps) {
  const theme = useTheme();

  const content = (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.backgroundElevated,
          borderColor: theme.colors.border,
        },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.symbol, { color: theme.colors.textPrimary }]}>
          {symbol ?? '—'}
        </Text>
        {convictionBand && <Badge label={convictionBand} variant="info" size="sm" />}
        {sector && (
          <Text style={[styles.sector, { color: theme.colors.textMuted }]}>{sector}</Text>
        )}
      </View>
      <View style={styles.metrics}>
        <View style={styles.metric}>
          <Text style={[styles.label, { color: theme.colors.textMuted }]}>Qty</Text>
          <MetricValue value={quantity} format="number" size="sm" />
        </View>
        <View style={styles.metric}>
          <Text style={[styles.label, { color: theme.colors.textMuted }]}>Mkt Val</Text>
          <MetricValue value={marketValue} format="currency" size="sm" />
        </View>
        <View style={styles.metric}>
          <Text style={[styles.label, { color: theme.colors.textMuted }]}>P&L</Text>
          <MetricValue value={unrealizedPnl} format="currency" colorize size="sm" />
        </View>
        <View style={styles.metric}>
          <Text style={[styles.label, { color: theme.colors.textMuted }]}>Wt%</Text>
          <MetricValue value={weightPct} format="percent" size="sm" />
        </View>
      </View>
      <Text style={[styles.cost, { color: theme.colors.textMuted }]}>
        Avg {avgCost.toFixed(2)}
      </Text>
    </View>
  );

  if (onPress) {
    return (
      <Pressable onPress={onPress} accessibilityRole="button">
        {content}
      </Pressable>
    );
  }
  return content;
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 8,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  symbol: {
    fontSize: 16,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  sector: {
    fontSize: 11,
    marginLeft: 'auto',
  },
  metrics: {
    flexDirection: 'row',
    gap: 16,
  },
  metric: {
    gap: 2,
  },
  label: {
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  cost: {
    fontSize: 11,
    fontFamily: 'monospace',
  },
});
