import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { RiskIndicatorProps } from '@pipm/types';

const RISK_COLORS: Record<string, string> = {
  LOW: '#3dba7a',
  MEDIUM: '#d4a017',
  HIGH: '#e07b39',
  CRITICAL: '#c0392b',
  UNKNOWN: '#5c6d82',
};

export function RiskIndicator({
  riskLevel,
  alerts,
  maxAlerts = 3,
  onPress,
}: RiskIndicatorProps) {
  const theme = useTheme();
  const color = RISK_COLORS[riskLevel] ?? RISK_COLORS.UNKNOWN;
  const visibleAlerts = alerts.slice(0, maxAlerts);

  const content = (
    <View
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.backgroundPanel,
          borderColor: theme.colors.border,
        },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.label, { color: theme.colors.textMuted }]}>RISK</Text>
        <View style={[styles.levelBadge, { borderColor: color, backgroundColor: `${color}22` }]}>
          <Text style={[styles.level, { color }]}>{riskLevel}</Text>
        </View>
      </View>
      {visibleAlerts.map((alert) => (
        <View key={alert.code} style={styles.alert}>
          <Text style={[styles.alertCode, { color: theme.colors.textSecondary }]}>
            {alert.code}
          </Text>
          <Text style={[styles.alertMsg, { color: theme.colors.textPrimary }]} numberOfLines={1}>
            {alert.message}
          </Text>
        </View>
      ))}
      {alerts.length > maxAlerts && (
        <Text style={[styles.more, { color: theme.colors.textMuted }]}>
          +{alerts.length - maxAlerts} more
        </Text>
      )}
    </View>
  );

  if (onPress) {
    return <Pressable onPress={onPress}>{content}</Pressable>;
  }
  return content;
}

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 6,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
  },
  levelBadge: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  level: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  alert: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
  },
  alertCode: {
    fontSize: 10,
    fontFamily: 'monospace',
    width: 80,
  },
  alertMsg: {
    fontSize: 12,
    flex: 1,
  },
  more: {
    fontSize: 11,
  },
});
