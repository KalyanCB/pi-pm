import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '@pipm/theme';
import {
  useDashboard,
  useNavHistory,
  usePilotHealthQuery,
  usePilotRecommendationsQuery,
  useTrustDashboardQuery,
  useCommitteeScreen,
  usePortfolioScreen,
  useUiStore,
} from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { LoadingState } from '../feedback/LoadingState';
import { ErrorState } from '../feedback/ErrorState';
import { PortfolioSummaryCard } from '../molecules/dashboard/PortfolioSummaryCard';
import { NavTrendCard } from '../molecules/dashboard/NavTrendCard';
import { AlphaCard } from '../molecules/dashboard/AlphaCard';
import { CashCard } from '../molecules/dashboard/CashCard';
import { RiskCard } from '../molecules/dashboard/RiskCard';
import { PendingExitCard } from '../molecules/dashboard/PendingExitCard';
import { PilotHealthCard } from '../molecules/dashboard/PilotHealthCard';
import { RecommendationSummaryCard } from '../molecules/dashboard/RecommendationSummaryCard';
import { TrustScoreCard } from '../molecules/TrustScoreCard';
import { TrustIndicatorStrip } from '../molecules/TrustIndicatorStrip';
import { SparklineChart } from '../charts/SparklineChart';
import { DonutChart } from '../charts/DonutChart';
import { BarChart } from '../charts/BarChart';
import { HighConcernBanner } from '../molecules/HighConcernBanner';
import { Button } from '../atoms/Button';

export function DashboardScreen() {
  const theme = useTheme();
  const router = useRouter();
  const toggleCopilot = useUiStore((s) => s.toggleCopilotPanel);
  const setTab = useUiStore((s) => s.setRecommendationTab);

  const { dashboard, trustScore, isLoading, isError, error, refetch } = useDashboard();
  const { navSeries, alphaSeries } = useNavHistory();
  const pilotHealth = usePilotHealthQuery();
  const pilotRecs = usePilotRecommendationsQuery();
  const trustDash = useTrustDashboardQuery();
  const { highConcernPackets } = useCommitteeScreen();
  const { positions } = usePortfolioScreen();

  const trustTrend = (trustDash.data?.trend_weekly ?? [])
    .map((p) => p.overall_trust_score)
    .filter((v): v is number => v != null);

  const today = pilotRecs.data?.today ?? {};
  const actionCounts = today.actions ?? {};
  const buyCount = today.buy_count ?? actionCounts.BUY ?? 0;
  const watchCount = today.watch_count ?? actionCounts.WATCH ?? 0;
  const exitCount = today.exit_count ?? actionCounts.EXIT_APPROVED ?? 0;

  const allocation = positions
    .filter((p) => (p.weight_pct ?? 0) > 0)
    .map((p) => ({ label: p.symbol ?? '—', value: p.weight_pct ?? 0 }));

  const distItems = [
    { label: 'BUY', value: buyCount },
    { label: 'WATCH', value: watchCount },
    { label: 'EXIT', value: exitCount },
  ];

  return (
    <InvestorScreenShell
      title="Portfolio Console"
      subtitle="Health · Recommendations · Committee · Trust"
      headerRight={<Button label="Copilot" onPress={toggleCopilot} variant="ghost" />}
    >
      {isLoading && <LoadingState message="Loading portfolio health…" />}
      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load dashboard'}
          onRetry={() => void refetch()}
        />
      )}

      {highConcernPackets.length > 0 && (
        <Pressable onPress={() => router.push('/committee')}>
          <HighConcernBanner
            committees={highConcernPackets.flatMap(
              (p) => p.payload.committee_advisory?.high_concern_committees ?? [],
            )}
          />
        </Pressable>
      )}

      {dashboard && (
        <>
          <Text style={[styles.section, { color: theme.colors.textMuted }]}>PORTFOLIO HEALTH</Text>
          <View style={styles.grid}>
            <PortfolioSummaryCard
              nav={dashboard.nav}
              todayChangePct={dashboard.today_change_pct}
              activePositions={dashboard.active_positions}
              onPress={() => router.push('/portfolio')}
            />
            <CashCard cashPct={dashboard.cash_pct} />
            <AlphaCard alpha={dashboard.alpha_pct} series={alphaSeries} />
          </View>

          <View style={styles.grid}>
            <NavTrendCard nav={dashboard.nav} series={navSeries} />
            <View style={styles.trustCol}>
              <TrustScoreCard score={trustScore} showBreakdown />
              <TrustIndicatorStrip trust={trustDash.data?.trust ?? undefined} compact />
              {trustTrend.length > 1 && (
                <SparklineChart data={trustTrend} height={60} emptyLabel="Building trust history" />
              )}
            </View>
            <RiskCard
              riskLevel={dashboard.risk_level}
              alerts={dashboard.risk_alerts}
              onPress={() => router.push('/portfolio')}
            />
          </View>

          <Text style={[styles.section, { color: theme.colors.textMuted }]}>REQUIRES ATTENTION</Text>
          <View style={styles.grid}>
            <PendingExitCard
              count={dashboard.pending_exits}
              onPress={() => {
                setTab('EXIT_APPROVED');
                router.push('/recommendations');
              }}
            />
            {pilotHealth.data && (
              <PilotHealthCard
                gateOpen={pilotHealth.data.analytics_gate_open}
                riskLevel={pilotHealth.data.risk_level}
                alertCount={pilotHealth.data.alerts?.length ?? 0}
              />
            )}
            <RecommendationSummaryCard
              buyCount={buyCount}
              watchCount={watchCount}
              exitCount={exitCount}
              onPressBuy={() => {
                setTab('BUY');
                router.push('/recommendations');
              }}
              onPressWatch={() => {
                setTab('WATCH');
                router.push('/recommendations');
              }}
            />
          </View>

          <Text style={[styles.section, { color: theme.colors.textMuted }]}>VISUALIZATIONS</Text>
          <View style={styles.chartRow}>
            <View style={[styles.chartBox, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
              <Text style={[styles.chartTitle, { color: theme.colors.textMuted }]}>ALLOCATION</Text>
              <DonutChart segments={allocation} />
            </View>
            <View style={[styles.chartBox, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
              <Text style={[styles.chartTitle, { color: theme.colors.textMuted }]}>TODAY'S DISTRIBUTION</Text>
              <BarChart
                items={distItems.map((d) => ({ label: d.label, value: d.value }))}
                emptyLabel="No recommendations today"
              />
            </View>
          </View>

          {dashboard.reconciliation_status && dashboard.reconciliation_status !== 'PASS' && (
            <Text style={[styles.recon, { color: theme.colors.warning }]}>
              Reconciliation: {dashboard.reconciliation_status} — some analytics may be unavailable
            </Text>
          )}
        </>
      )}
    </InvestorScreenShell>
  );
}

const styles = StyleSheet.create({
  section: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
    marginTop: 4,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  trustCol: {
    flex: 1,
    minWidth: 200,
    gap: 8,
  },
  chartRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  chartBox: {
    flex: 1,
    minWidth: 260,
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 8,
  },
  chartTitle: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  recon: {
    fontSize: 12,
    padding: 8,
  },
});
