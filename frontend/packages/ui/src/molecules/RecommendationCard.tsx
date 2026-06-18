import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { RecommendationCardProps } from '@pipm/types';
import { Badge } from '../atoms/Badge';
import { ConvictionBadge } from './ConvictionBadge';
import { RecommendationReasonList } from './RecommendationReasonList';
import { HighConcernBanner } from './HighConcernBanner';
import { CommitteeAdvisoryCard } from './CommitteeAdvisoryCard';

export function RecommendationCard({
  symbol,
  action,
  rank,
  convictionScore,
  convictionBand,
  reasonCodes,
  committeeAdvisory,
  committeeFindings = [],
  layout = 'card',
  embedded = false,
  onPress,
  entryLow,
  entryHigh,
  stopAdvisory,
  stopCritical,
  levelsBasis,
  ltp,
}: RecommendationCardProps) {
  const theme = useTheme();
  const isRow = layout === 'row';
  const hasLevels = entryLow != null && entryHigh != null;
  const inr = (v: number | null | undefined) =>
    v == null ? '—' : `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

  const content = (
    <View
      style={[
        styles.card,
        isRow ? styles.row : styles.column,
        embedded && styles.embedded,
        {
          backgroundColor: embedded
            ? 'transparent'
            : theme.colors.backgroundElevated,
          borderColor: embedded
            ? 'transparent'
            : committeeAdvisory?.high_concern
              ? theme.colors.highConcern
              : theme.colors.border,
        },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.symbol, { color: theme.colors.textPrimary }]}>{symbol}</Text>
        <Badge
          label={action}
          variant={
            action === 'BUY'
              ? 'success'
              : action === 'WATCH'
                ? 'warning'
                : action === 'EXIT_APPROVED'
                  ? 'danger'
                  : 'default'
          }
        />
        {rank !== null && (
          <Text style={[styles.rank, { color: theme.colors.textMuted }]}>#{rank}</Text>
        )}
        <ConvictionBadge score={convictionScore} band={convictionBand} size="sm" />
      </View>
      {ltp != null && (
        <Text style={[styles.ltp, { color: theme.colors.textPrimary }]}>
          LTP {inr(ltp)}
        </Text>
      )}
      {hasLevels && (
        <Text style={[styles.levels, { color: theme.colors.textSecondary }]}>
          Entry {inr(entryLow)}–{inr(entryHigh)}
          {stopAdvisory != null ? `  ·  SL ${inr(stopAdvisory)}` : ''}
          {stopCritical != null ? ` / ${inr(stopCritical)}` : ''}
          {levelsBasis === 'indicative' ? '  (indicative)' : ''}
        </Text>
      )}
      <RecommendationReasonList reasonCodes={reasonCodes} />
      {committeeAdvisory && isRow && (
        <>
          {committeeAdvisory.high_concern && (
            <HighConcernBanner
              committees={committeeAdvisory.high_concern_committees}
              displayNames={committeeAdvisory.display_names}
              compact
            />
          )}
          {committeeAdvisory.cro_advisory_action && (
            <Text style={[styles.cro, { color: theme.colors.textSecondary }]}>
              CRO: {committeeAdvisory.cro_advisory_action}
            </Text>
          )}
        </>
      )}
      {committeeAdvisory && !isRow && (
        <CommitteeAdvisoryCard advisory={committeeAdvisory} findings={committeeFindings} />
      )}
    </View>
  );

  if (onPress) {
    return (
      <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${symbol} ${action}`}>
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
  embedded: {
    borderWidth: 0,
    borderRadius: 0,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  column: {},
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  symbol: {
    fontSize: 16,
    fontWeight: '700',
    fontFamily: 'monospace',
    minWidth: 80,
  },
  rank: {
    fontSize: 12,
    fontFamily: 'monospace',
  },
  cro: {
    fontSize: 11,
  },
  levels: {
    fontSize: 11,
    fontFamily: 'monospace',
  },
  ltp: {
    fontSize: 12,
    fontFamily: 'monospace',
    fontWeight: '600',
  },
});
