import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { MetricCard } from '../../layout/MetricCard';
import { MetricValue } from '../../atoms/MetricValue';

export interface PendingExitCardProps {
  count: number;
  onPress?: () => void;
}

export function PendingExitCard({ count, onPress }: PendingExitCardProps) {
  const theme = useTheme();
  const alert = count > 0;
  return (
    <MetricCard label="PENDING EXITS" alert={alert} onPress={onPress}>
      <MetricValue value={count} format="integer" size="lg" />
      {alert && (
        <Text style={[styles.hint, { color: theme.colors.highConcern }]}>
          Review exit recommendations
        </Text>
      )}
    </MetricCard>
  );
}

const styles = StyleSheet.create({
  hint: {
    fontSize: 11,
    fontWeight: '600',
  },
});
