import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { MetricCard } from '../../layout/MetricCard';
import { MetricValue } from '../../atoms/MetricValue';

export interface PortfolioSummaryCardProps {
  nav: number | null;
  todayChangePct: number | null;
  activePositions: number;
  onPress?: () => void;
}

export function PortfolioSummaryCard({
  nav,
  todayChangePct,
  activePositions,
  onPress,
}: PortfolioSummaryCardProps) {
  const theme = useTheme();
  return (
    <MetricCard label="PORTFOLIO" highlight onPress={onPress} style={styles.wide}>
      <MetricValue value={nav} format="currency" size="lg" />
      <View style={styles.row}>
        <MetricValue value={todayChangePct} format="percent" colorize size="sm" />
        <Text style={[styles.meta, { color: theme.colors.textMuted }]}>
          {activePositions} positions
        </Text>
      </View>
    </MetricCard>
  );
}

const styles = StyleSheet.create({
  wide: {
    minWidth: 200,
    flex: 2,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  meta: {
    fontSize: 11,
  },
});
