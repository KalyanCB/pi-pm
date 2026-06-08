import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { CommitteeAdvisoryOverlay, CommitteeReviewFinding } from '@pipm/types';
import { Badge } from '../atoms/Badge';
import { HighConcernBanner } from './HighConcernBanner';

export interface CommitteeAdvisoryCardProps {
  advisory: CommitteeAdvisoryOverlay;
  machineAction?: string;
  compact?: boolean;
  findings?: CommitteeReviewFinding[];
}

export function CommitteeAdvisoryCard({
  advisory,
  machineAction,
  compact = false,
  findings = [],
}: CommitteeAdvisoryCardProps) {
  const theme = useTheme();
  const [expanded, setExpanded] = useState<string | null>(null);

  const findingsByCode = Object.fromEntries(
    findings.map((f) => [f.committee_code, f]),
  );

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
          {Object.entries(advisory.committee_actions).map(([code, action]) => {
            const finding = findingsByCode[code];
            const isOpen = expanded === code;
            const hasFindings =
              finding &&
              finding.findings &&
              !finding.findings.includes('abstain') &&
              !finding.findings.includes('validation failed');

            return (
              <View key={code}>
                <TouchableOpacity
                  style={styles.actionRow}
                  onPress={() => hasFindings ? setExpanded(isOpen ? null : code) : undefined}
                  activeOpacity={hasFindings ? 0.7 : 1}
                >
                  <Text style={[styles.code, { color: theme.colors.textSecondary }]}>
                    {advisory.display_names[code] ?? code}
                  </Text>
                  <View style={styles.actionRight}>
                    <Badge label={action} size="sm" />
                    {hasFindings && (
                      <Text style={[styles.chevron, { color: theme.colors.textMuted }]}>
                        {isOpen ? '▲' : '▼'}
                      </Text>
                    )}
                  </View>
                </TouchableOpacity>

                {isOpen && hasFindings && finding && (
                  <View
                    style={[
                      styles.findingBox,
                      { backgroundColor: theme.colors.background, borderColor: theme.colors.border },
                    ]}
                  >
                    <Text style={[styles.findingText, { color: theme.colors.textPrimary }]}>
                      {finding.findings}
                    </Text>
                    {finding.confidence != null && (
                      <Text style={[styles.confidence, { color: theme.colors.textMuted }]}>
                        Confidence: {(finding.confidence * 100).toFixed(0)}%
                      </Text>
                    )}
                  </View>
                )}
              </View>
            );
          })}
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
    paddingVertical: 2,
  },
  actionRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  code: {
    fontSize: 11,
    flex: 1,
  },
  chevron: {
    fontSize: 10,
  },
  findingBox: {
    borderWidth: 1,
    borderRadius: 4,
    padding: 8,
    marginTop: 4,
    marginBottom: 4,
    gap: 4,
  },
  findingText: {
    fontSize: 12,
    lineHeight: 17,
  },
  confidence: {
    fontSize: 10,
    marginTop: 2,
  },
});
