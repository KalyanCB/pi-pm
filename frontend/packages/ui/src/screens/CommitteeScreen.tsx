import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '@pipm/theme';
import { useCommitteeScreen, useUiStore } from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { LoadingState } from '../feedback/LoadingState';
import { ErrorState } from '../feedback/ErrorState';
import { Badge } from '../atoms/Badge';
import { CommitteeConsensusCard } from '../molecules/CommitteeConsensusCard';
import { CommitteeReportPanel } from '../molecules/CommitteeReportPanel';
import { HighConcernBanner } from '../molecules/HighConcernBanner';
import { Button } from '../atoms/Button';

export function CommitteeScreen() {
  const theme = useTheme();
  const router = useRouter();
  const toggleCopilot = useUiStore((s) => s.toggleCopilotPanel);
  const openCopilot = useUiStore((s) => s.openCopilotWithQuestion);
  const { review, packets, highConcernPackets, report, isLoading, isError, error, refetch } =
    useCommitteeScreen();

  return (
    <InvestorScreenShell
      title="Investment Committee"
      subtitle="Advisory · HIGH_CONCERN · Governance"
      headerRight={<Button label="Copilot" onPress={toggleCopilot} variant="ghost" />}
    >
      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load committee data'}
          onRetry={() => void refetch()}
        />
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
              />
            </Pressable>
          ))}
        </View>
      )}

      <Text style={[styles.section, { color: theme.colors.textMuted }]}>
        ALL COMMITTEE ACTIONS ({packets.length})
      </Text>
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
});
