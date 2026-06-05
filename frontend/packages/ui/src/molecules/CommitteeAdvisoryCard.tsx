import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { CommitteeAdvisoryOverlay } from '@pipm/types';
import { Badge } from '../atoms/Badge';
import { HighConcernBanner } from './HighConcernBanner';

export interface CommitteeAdvisoryCardProps {
  advisory: CommitteeAdvisoryOverlay;
  machineAction?: string;
  compact?: boolean;
}

export function CommitteeAdvisoryCard({
  advisory,
  machineAction,
  compact = false,
}: CommitteeAdvisoryCardProps) {
  const theme = useTheme();

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
      {machineAction && (
        <View style={styles.row}>
          <Text style={[styles.label, { color: theme.colors.textMuted }]}>Engine</Text>
          <Badge label={machineAction} variant="info" />
        </View>
      )}
      <View style={styles.row}>
        <Text style={[styles.label, { color: theme.colors.textMuted }]}>CRO</Text>
        <Badge
          label={advisory.cro_advisory_action ?? '—'}
          variant={advisory.high_concern ? 'danger' : 'default'}
        />
      </View>
      {advisory.high_concern && (
        <HighConcernBanner
          committees={advisory.high_concern_committees}
          displayNames={advisory.display_names}
          compact={compact}
        />
      )}
      {!compact && Object.keys(advisory.committee_actions).length > 0 && (
        <View style={styles.actions}>
          {Object.entries(advisory.committee_actions).map(([code, action]) => (
            <View key={code} style={styles.actionRow}>
              <Text style={[styles.code, { color: theme.colors.textSecondary }]}>
                {advisory.display_names[code] ?? code}
              </Text>
              <Badge label={action} size="sm" />
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 10,
    gap: 8,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    width: 48,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  actions: {
    gap: 4,
    marginTop: 4,
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
