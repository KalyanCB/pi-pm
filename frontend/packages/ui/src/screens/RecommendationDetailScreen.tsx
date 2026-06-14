import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import {
  useRecommendationDetail,
  useTrustQuery,
  useApproveRecommendation,
  useRejectRecommendation,
  useUiStore,
  defaultStrategyName,
} from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { LoadingState } from '../feedback/LoadingState';
import { ErrorState } from '../feedback/ErrorState';
import { Badge } from '../atoms/Badge';
import { ConvictionBadge } from '../molecules/ConvictionBadge';
import { RecommendationReasonList } from '../molecules/RecommendationReasonList';
import { TradeLevelsCard } from '../molecules/TradeLevelsCard';
import { CommitteeAdvisoryCard } from '../molecules/CommitteeAdvisoryCard';
import { TrustIndicatorStrip } from '../molecules/TrustIndicatorStrip';
import { ReviewStepper } from '../molecules/ReviewStepper';
import { ApprovalActionBar } from '../molecules/ApprovalActionBar';
import { HighConcernBanner } from '../molecules/HighConcernBanner';

export interface RecommendationDetailScreenProps {
  symbol: string;
  runId?: string;
}

export function RecommendationDetailScreen({ symbol, runId }: RecommendationDetailScreenProps) {
  const theme = useTheme();
  const openCopilot = useUiStore((s) => s.openCopilotWithQuestion);
  const { result, strategy, committeeAdvisory, committeeFindings, machineAction, isLoading, isError, error, refetch } =
    useRecommendationDetail(symbol, runId);
  const trust = useTrustQuery(strategy);
  const approve = useApproveRecommendation();
  const reject = useRejectRecommendation();

  const action = result?.action ?? 'WATCH';
  const loading = approve.isPending || reject.isPending;

  return (
    <InvestorScreenShell
      title={symbol}
      subtitle={`${action} · ${strategy ?? defaultStrategyName()}`}
    >
      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load recommendation'}
          onRetry={() => void refetch()}
        />
      )}

      {result && (
        <>
          <ReviewStepper engineReviewed committeeReviewed={!!committeeAdvisory} />

          <View style={styles.header}>
            <Badge
              label={action}
              variant={
                action === 'BUY' ? 'success' : action === 'WATCH' ? 'warning' : 'danger'
              }
            />
            {result.rank !== null && (
              <Text style={[styles.rank, { color: theme.colors.textMuted }]}>Rank #{result.rank}</Text>
            )}
            <ConvictionBadge score={result.conviction_score} band={result.conviction_band} />
          </View>

          <View style={[styles.trustBox, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
            <Text style={[styles.trustLabel, { color: theme.colors.textMuted }]}>
              CAN I TRUST THIS?
              {trust.data?.overall_trust_score != null
                ? ` — Overall ${(trust.data.overall_trust_score * 100).toFixed(1)}%`
                : ' — Trust metrics loading'}
            </Text>
            <TrustIndicatorStrip trust={trust.data} />
          </View>

          {committeeAdvisory?.high_concern && (
            <HighConcernBanner
              committees={committeeAdvisory.high_concern_committees}
              displayNames={committeeAdvisory.display_names}
            />
          )}

          <View style={[styles.section, { borderColor: theme.colors.border }]}>
            <Text style={[styles.sectionTitle, { color: theme.colors.textMuted }]}>WHY RECOMMENDED</Text>
            <RecommendationReasonList reasonCodes={result.reason_codes} />
          </View>

          <TradeLevelsCard
            entryLow={result.entry_low}
            entryHigh={result.entry_high}
            stopAdvisory={result.stop_advisory}
            stopCritical={result.stop_critical}
            referenceClose={result.reference_close}
            atrPct={result.atr_pct}
            basis={result.levels_basis}
          />

          {committeeAdvisory && (
            <View style={[styles.section, { borderColor: theme.colors.border }]}>
              <Text style={[styles.sectionTitle, { color: theme.colors.textMuted }]}>COMMITTEE ADVISORY</Text>
              <CommitteeAdvisoryCard
                advisory={committeeAdvisory}
                machineAction={machineAction}
                findings={committeeFindings}
              />
            </View>
          )}

          <ApprovalActionBar
            action={action as 'BUY' | 'WATCH' | 'EXIT_APPROVED'}
            loading={loading}
            onApprove={() => approve.mutate({ resultId: result.id })}
            onReject={(note) => reject.mutate({ resultId: result.id, note })}
            onAskCopilot={() =>
              openCopilot(`Why is ${symbol} a ${action} today? What should I consider before approving?`)
            }
          />

          {(approve.isSuccess || reject.isSuccess) && (
            <Text style={[styles.success, { color: theme.colors.positive }]}>
              Decision recorded successfully
            </Text>
          )}
        </>
      )}
    </InvestorScreenShell>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
  },
  rank: {
    fontSize: 12,
    fontFamily: 'monospace',
  },
  trustBox: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 8,
  },
  trustLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  section: {
    borderTopWidth: 1,
    paddingTop: 12,
    gap: 8,
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  success: {
    fontSize: 13,
    fontWeight: '600',
    textAlign: 'center',
  },
});
