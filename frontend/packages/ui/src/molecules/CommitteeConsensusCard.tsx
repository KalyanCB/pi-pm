import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { CommitteeAdvisoryOverlay } from '@pipm/types';
import { Badge } from '../atoms/Badge';
import { HighConcernBanner } from './HighConcernBanner';

export interface CommitteeConsensusCardProps {
  symbol: string;
  advisory: CommitteeAdvisoryOverlay;
  machineAction?: string;
  onPress?: () => void;
}

export function CommitteeConsensusCard({
  symbol,
  advisory,
  machineAction,
}: CommitteeConsensusCardProps) {
  const theme = useTheme();

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: advisory.high_concern ? theme.colors.highConcernBg : theme.colors.backgroundPanel,
          borderColor: advisory.high_concern ? theme.colors.highConcern : theme.colors.border,
          borderLeftWidth: advisory.high_concern ? 3 : 1,
        },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.symbol, { color: theme.colors.textPrimary }]}>{symbol}</Text>
        {machineAction && <Badge label={machineAction} variant="info" size="sm" />}
        <Badge
          label={advisory.cro_advisory_action ?? '—'}
          variant={advisory.high_concern ? 'danger' : 'default'}
        />
      </View>
      {advisory.high_concern && (
        <HighConcernBanner
          committees={advisory.high_concern_committees}
          displayNames={advisory.display_names}
        />
      )}
      <View style={styles.actions}>
        {Object.entries(advisory.committee_actions).map(([code, action]) => (
          <View key={code} style={styles.actionRow}>
            <Text style={[styles.code, { color: theme.colors.textSecondary }]}>
              {advisory.display_names[code] ?? code}
            </Text>
            <Badge
              label={action}
              variant={
                action === 'APPROVE' ? 'success' : action === 'REJECT' ? 'danger' : 'warning'
              }
              size="sm"
            />
          </View>
        ))}
      </View>
    </View>
  );
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
    flexWrap: 'wrap',
  },
  symbol: {
    fontSize: 15,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  actions: {
    gap: 4,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  code: {
    fontSize: 11,
  },
});
