import React from 'react';
import { Text, StyleSheet, View } from 'react-native';
import { useTheme } from '@pipm/theme';
import { MetricCard } from '../../layout/MetricCard';
import { Badge } from '../../atoms/Badge';

export interface PilotHealthCardProps {
  gateOpen: boolean;
  riskLevel: string;
  alertCount: number;
  onPress?: () => void;
}

export function PilotHealthCard({
  gateOpen,
  riskLevel,
  alertCount,
  onPress,
}: PilotHealthCardProps) {
  const theme = useTheme();
  return (
    <MetricCard label="PILOT HEALTH" alert={!gateOpen || alertCount > 0} onPress={onPress}>
      <View style={styles.row}>
        <Badge
          label={gateOpen ? 'GATE OPEN' : 'GATE CLOSED'}
          variant={gateOpen ? 'success' : 'warning'}
        />
        <Badge label={riskLevel} variant="info" size="sm" />
      </View>
      {alertCount > 0 && (
        <Text style={[styles.alerts, { color: theme.colors.warning }]}>
          {alertCount} active alert{alertCount !== 1 ? 's' : ''}
        </Text>
      )}
    </MetricCard>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  alerts: {
    fontSize: 11,
    fontWeight: '600',
  },
});
