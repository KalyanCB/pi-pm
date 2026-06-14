import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme, useBreakpoint } from '@pipm/theme';
import {
  useRecommendationCards,
  useRegimeQuery,
  useUiStore,
  useTrustQuery,
  useExitMonitorQuery,
  useConfirmExit,
  useRejectExit,
  formatTrendRegime,
  formatVolRegime,
} from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { MasterDetailLayout } from '../layout/MasterDetailLayout';
import { LoadingState } from '../feedback/LoadingState';
import { ErrorState } from '../feedback/ErrorState';
import { RecommendationHistoryCard } from '../molecules/RecommendationHistoryCard';
import { ExitMonitorCard } from '../molecules/ExitMonitorCard';
import { RecommendationDetailScreen } from './RecommendationDetailScreen';
import { TrustIndicatorStrip } from '../molecules/TrustIndicatorStrip';
import { Button } from '../atoms/Button';
import { DatePicker } from '../atoms/DatePicker';

const TABS = ['BUY', 'WATCH', 'EXIT_APPROVED'] as const;

function hasExecutionHistory(
  execution: ReturnType<typeof useRecommendationCards>['cards'][number]['execution'],
) {
  if (!execution) return false;
  const approvals = execution.approvals ?? [];
  const trades = execution.trades ?? [];
  return (
    approvals.length > 0 ||
    trades.length > 0 ||
    !!execution.position ||
    !!execution.outcome
  );
}

function tabLabel(tab: (typeof TABS)[number], count: number) {
  const name = tab === 'EXIT_APPROVED' ? 'EXIT' : tab;
  return `${name} ${count}`;
}

export function RecommendationsScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { isDesktop } = useBreakpoint();
  const tab = useUiStore((s) => s.recommendationTab);
  const setTab = useUiStore((s) => s.setRecommendationTab);
  const selected = useUiStore((s) => s.selectedRecommendation);
  const setSelected = useUiStore((s) => s.setSelectedRecommendation);
  const toggleCopilot = useUiStore((s) => s.toggleCopilotPanel);
  const {
    cards,
    tabCounts,
    strategy,
    asOfDate,
    availableDates,
    latestDate,
    selectedAsOfDate,
    setRecommendationAsOfDate,
    isLoading,
    isError,
    error,
    refetch,
  } = useRecommendationCards();
  const trust = useTrustQuery(strategy);
  const regime = useRegimeQuery(asOfDate);
  const isViewingLatest = !selectedAsOfDate || selectedAsOfDate === latestDate;
  const exitMonitor = useExitMonitorQuery(asOfDate, !isViewingLatest);
  const confirmExit = useConfirmExit();
  const rejectExit = useRejectExit();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const exitMonitorCount = exitMonitor.data?.length ?? 0;
  const displayTabCounts = useMemo(
    () => ({
      ...tabCounts,
      EXIT_APPROVED: tabCounts.EXIT_APPROVED + exitMonitorCount,
    }),
    [tabCounts, exitMonitorCount],
  );

  useEffect(() => {
    setExpandedId(null);
  }, [tab, asOfDate]);

  const dateBounds = useMemo(() => {
    if (!availableDates.length) return { min: undefined, max: undefined };
    return {
      min: availableDates[availableDates.length - 1],
      max: availableDates[0],
    };
  }, [availableDates]);

  const subtitle = (
    <View style={styles.subtitleBlock}>
      <View style={styles.subtitleRow}>
        <Text style={[styles.subtitleText, { color: theme.colors.textMuted }]}>
          {asOfDate} · Decision support
        </Text>
        {regime.data && (
          <>
            <Text style={[styles.subtitleSep, { color: theme.colors.textMuted }]}>·</Text>
            <Text
              style={[
                styles.regimeTag,
                {
                  color:
                    regime.data.trend_regime === 'BULL'
                      ? theme.colors.positive
                      : regime.data.trend_regime === 'BEAR'
                        ? theme.colors.negative
                        : theme.colors.textSecondary,
                },
              ]}
            >
              {formatTrendRegime(regime.data.trend_regime)}
            </Text>
            <Text style={[styles.subtitleSep, { color: theme.colors.textMuted }]}>·</Text>
            <Text style={[styles.regimeTag, { color: theme.colors.textSecondary }]}>
              {formatVolRegime(regime.data.vol_regime)}
            </Text>
          </>
        )}
      </View>
      <View style={styles.dateRow}>
        <DatePicker
          value={asOfDate}
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

  const handleSelect = (card: (typeof cards)[number]) => {
    setSelected({
      id: card.id,
      symbol: card.symbol,
      runId: card.runId,
      action: card.action as typeof tab,
    });
    if (!isDesktop) {
      router.push(`/recommendations/${card.symbol}?runId=${card.runId}`);
    }
  };

  const master = (
    <>
      <View style={styles.tabs}>
        {TABS.map((t) => (
          <Pressable
            key={t}
            onPress={() => setTab(t)}
            style={[
              styles.tab,
              {
                backgroundColor: tab === t ? theme.colors.sidebarActive : theme.colors.backgroundPanel,
                borderColor: theme.colors.border,
              },
            ]}
          >
            <Text style={[styles.tabText, { color: tab === t ? theme.colors.accent : theme.colors.textMuted }]}>
              {tabLabel(t, displayTabCounts[t])}
            </Text>
          </Pressable>
        ))}
      </View>
      <TrustIndicatorStrip trust={trust.data} compact />

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load recommendations'}
          onRetry={() => void refetch()}
        />
      )}
      {tab === 'EXIT_APPROVED' && (
        <View style={styles.exitSection}>
          <Text style={[styles.sectionLabel, { color: theme.colors.textMuted }]}>
            EXIT MONITOR · {asOfDate}
          </Text>
          {exitMonitor.isLoading && <LoadingState />}
          {exitMonitor.isError && (
            <ErrorState
              message="Failed to load exit monitor candidates"
              onRetry={() => void exitMonitor.refetch()}
            />
          )}
          {!exitMonitor.isLoading && !exitMonitor.isError && exitMonitorCount === 0 && (
            <Text style={[styles.emptyHint, { color: theme.colors.textMuted }]}>
              No exit monitor signals for this day. Open positions are evaluated daily for rank drop, time stop, and other triggers.
            </Text>
          )}
          <View style={styles.list}>
            {(exitMonitor.data ?? []).map((exit) => (
              <ExitMonitorCard
                key={exit.id}
                exit={exit}
                onConfirm={
                  exit.status === 'PENDING' && isViewingLatest
                    ? () => confirmExit.mutate(exit.id)
                    : undefined
                }
                onReject={
                  exit.status === 'PENDING' && isViewingLatest
                    ? () => rejectExit.mutate({ exitId: exit.id })
                    : undefined
                }
                confirming={confirmExit.isPending}
                rejecting={rejectExit.isPending}
              />
            ))}
          </View>
        </View>
      )}

      {tab === 'EXIT_APPROVED' && cards.length > 0 && (
        <Text style={[styles.sectionLabel, { color: theme.colors.textMuted }]}>
          ENGINE EXIT_APPROVED
        </Text>
      )}

      {!isLoading && !isError && cards.length === 0 && tab !== 'EXIT_APPROVED' && (
        <Text style={[styles.empty, { color: theme.colors.textMuted }]}>
          No {tab} recommendations for {asOfDate}.
        </Text>
      )}
      {!isLoading && !isError && cards.length === 0 && tab === 'EXIT_APPROVED' && exitMonitorCount === 0 && (
        <Text style={[styles.empty, { color: theme.colors.textMuted }]}>
          No exit signals for {asOfDate}.
        </Text>
      )}
      <View style={styles.list}>
        {cards.map((card) => {
          const showHistory = hasExecutionHistory(card.execution);
          return (
            <RecommendationHistoryCard
              key={card.id}
              symbol={card.symbol}
              action={card.action}
              rank={card.rank}
              convictionScore={card.convictionScore}
              convictionBand={card.convictionBand}
              reasonCodes={card.reasonCodes}
              entryLow={card.entryLow}
              entryHigh={card.entryHigh}
              stopAdvisory={card.stopAdvisory}
              stopCritical={card.stopCritical}
              levelsBasis={card.levelsBasis}
              committeeAdvisory={card.committeeAdvisory}
              committeeFindings={card.committeeFindings}
              lifecycleState={card.lifecycleState}
              execution={card.execution}
              hasExecutionHistory={showHistory}
              expanded={expandedId === card.id}
              onToggleExpand={() =>
                setExpandedId((id) => (id === card.id ? null : card.id))
              }
              onPress={() => handleSelect(card)}
            />
          );
        })}
      </View>
    </>
  );

  const detail =
    selected && isDesktop ? (
      <RecommendationDetailScreen symbol={selected.symbol} runId={selected.runId} />
    ) : null;

  return (
    <InvestorScreenShell
      title="Recommendations"
      subtitle={subtitle}
      headerRight={<Button label="Copilot" onPress={toggleCopilot} variant="ghost" />}
    >
      <MasterDetailLayout master={master} detail={detail} />
    </InvestorScreenShell>
  );
}

const styles = StyleSheet.create({
  subtitleBlock: {
    gap: 8,
  },
  subtitleRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 6,
  },
  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flexWrap: 'wrap',
  },
  subtitleText: {
    fontSize: 13,
  },
  subtitleSep: {
    fontSize: 13,
  },
  regimeTag: {
    fontSize: 13,
    fontWeight: '600',
  },
  latestLink: {
    fontSize: 12,
    fontWeight: '600',
  },
  tabs: {
    flexDirection: 'row',
    gap: 8,
  },
  tab: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  tabText: {
    fontSize: 12,
    fontWeight: '700',
  },
  exitSection: {
    gap: 10,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
  emptyHint: {
    fontSize: 12,
    lineHeight: 18,
  },
  list: {
    gap: 10,
  },
  empty: {
    fontSize: 13,
    padding: 16,
    textAlign: 'center',
  },
});
