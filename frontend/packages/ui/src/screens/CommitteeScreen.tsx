import React, { useMemo } from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '@pipm/theme';
import { useCommitteeScreen, useUiStore } from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { LoadingState } from '../feedback/LoadingState';
import { ErrorState } from '../feedback/ErrorState';
import { Badge } from '../atoms/Badge';
import { DatePicker } from '../atoms/DatePicker';
import { CommitteeConsensusCard } from '../molecules/CommitteeConsensusCard';
import { CommitteeReportPanel } from '../molecules/CommitteeReportPanel';
import { HighConcernBanner } from '../molecules/HighConcernBanner';
import { Button } from '../atoms/Button';

export function CommitteeScreen() {
  const theme = useTheme();
  const router = useRouter();
  const toggleCopilot = useUiStore((s) => s.toggleCopilotPanel);
  const openCopilot = useUiStore((s) => s.openCopilotWithQuestion);
  const {
    review,
    packets,
    highConcernPackets,
    report,
    findingsBySymbol,
    strategy,
    selectedAsOfDate,
    setRecommendationAsOfDate,
    availableDates,
    latestDate,
    isLoading,
    isError,
    error,
    refetch,
  } = useCommitteeScreen();

  const dateBounds = useMemo(() => {
    if (!availableDates.length) return { min: undefined, max: undefined };
    return { min: availableDates[availableDates.length - 1], max: availableDates[0] };
  }, [availableDates]);

  const pickerValue = selectedAsOfDate ?? review?.as_of_date ?? latestDate ?? '';

  const subtitle = (
    <View style={styles.subtitleBlock}>
      <Text style={[styles.subtitleText, { color: theme.colors.textMuted }]}>
        Advisory · HIGH_CONCERN · Governance{strategy ? ` · ${strategy}` : ''}
      </Text>
      <View style={styles.dateRow}>
        <DatePicker
          value={pickerValue}
          min={dateBounds.min}
          max={dateBounds.max}
          onChange={(d) => setRecommendationAsOfDate(d === latestDate ? null : d)}
        />
        {selectedAsOfDate && latestDate && (
          <Pressable onPress={() => setRecommendationAsOfDate(null)}>
            <Text style={[styles.latestLink, { color: theme.colors.accent }]}>Latest</Text>
          </Pressable>
        )}
      </View>
    </View>
  );

  return (
    <InvestorScreenShell
      title="Investment Committee"
      subtitle={subtitle}
      headerRight={<Button label="Copilot" onPress={toggleCopilot} variant="ghost" />}
    >
      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load committee data'}
          onRetry={() => void refetch()}
        />
      )}

      {!isLoading && !isError && !review && (
        <Text style={[styles.empty, { color: theme.colors.textMuted }]}>
          No committee review for {selectedAsOfDate ?? latestDate ?? 'this date'}. The committee
          runs on a subset of sessions — pick another date or return to Latest.
        </Text>
      )}

      {review && (
        <View style={[styles.header, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border }]}>
          <View style={styles.headerRow}>
            <Text style={[styles.date, { color: theme.colors.textPrimary }]}>{review.as_of_date}</Text>
            <Badge label={review.status} variant={review.status === 'COMPLETED' ? 'success' : 'warning'} />
          </View>
          <Text style={[styles.meta, { color: theme.colors.textMuted }]}>
            {review.candidates_reviewed} candidates · {packets.length} advisories
          </Text>
        </View>
      )}

      {highConcernPackets.length > 0 && (
        <View style={[styles.hero, { borderColor: theme.colors.highConcern, backgroundColor: theme.colors.highConcernBg }]}>
          <Text style={[styles.heroTitle, { color: theme.colors.highConcern }]}>
            HIGH CONCERN — {highConcernPackets.length} SYMBOL{highConcernPackets.length !== 1 ? 'S' : ''}
          </Text>
          <Text style={[styles.heroSub, { color: theme.colors.textSecondary }]}>
            Committee flagged elevated risk. Review before approving recommendations.
          </Text>
          {highConcernPackets.map((packet) => (
            <Pressable
              key={packet.packet_id}
              onPress={() => {
                openCopilot(`What concerns does the committee have about ${packet.symbol}?`);
                router.push('/recommendations');
              }}
            >
              <CommitteeConsensusCard
                symbol={packet.symbol}
                advisory={packet.payload.committee_advisory!}
                machineAction={packet.payload.recommendation?.action}
                findings={findingsBySymbol.get(packet.symbol) ?? []}
              />
            </Pressable>
          ))}
        </View>
      )}

      {review && (
        <Text style={[styles.section, { color: theme.colors.textMuted }]}>
          ALL COMMITTEE ACTIONS ({packets.length})
        </Text>
      )}
      <View style={styles.list}>
        {packets.map((packet) => (
          <View key={packet.packet_id}>
            {packet.payload.committee_advisory?.high_concern && (
              <HighConcernBanner
                committees={packet.payload.committee_advisory.high_concern_committees}
                displayNames={packet.payload.committee_advisory.display_names}
                compact
              />
            )}
            {packet.payload.committee_advisory && (
              <CommitteeConsensusCard
                symbol={packet.symbol}
                advisory={packet.payload.committee_advisory}
                machineAction={packet.payload.recommendation?.action}
                findings={findingsBySymbol.get(packet.symbol) ?? []}
              />
            )}
          </View>
        ))}
      </View>

      {report && <CommitteeReportPanel reports={report.reports} />}
    </InvestorScreenShell>
  );
}

const styles = StyleSheet.create({
  subtitleBlock: {
    gap: 8,
  },
  subtitleText: {
    fontSize: 13,
  },
  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flexWrap: 'wrap',
  },
  latestLink: {
    fontSize: 12,
    fontWeight: '600',
  },
  header: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 4,
  },
  headerRow: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
  },
  date: {
    fontSize: 16,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  meta: {
    fontSize: 12,
  },
  hero: {
    borderWidth: 2,
    borderLeftWidth: 4,
    borderRadius: 6,
    padding: 16,
    gap: 12,
  },
  heroTitle: {
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1,
  },
  heroSub: {
    fontSize: 13,
  },
  section: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  list: {
    gap: 10,
  },
  empty: {
    fontSize: 13,
    padding: 16,
    textAlign: 'center',
    lineHeight: 19,
  },
});
