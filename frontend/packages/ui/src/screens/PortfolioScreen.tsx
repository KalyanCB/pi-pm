import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useTheme } from '@pipm/theme';
import { usePortfolioScreen, useNavHistory, useUiStore } from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { LoadingState } from '../feedback/LoadingState';
import { ErrorState } from '../feedback/ErrorState';
import { MetricValue } from '../atoms/MetricValue';
import { PortfolioPositionCard } from '../molecules/PortfolioPositionCard';
import { SparklineChart } from '../charts/SparklineChart';
import { DonutChart } from '../charts/DonutChart';
import { BarChart } from '../charts/BarChart';
import { Button } from '../atoms/Button';

const TABS = ['Overview', 'Positions', 'Allocation', 'Performance', 'Attribution'] as const;

export function PortfolioScreen() {
  const theme = useTheme();
  const [section, setSection] = useState<(typeof TABS)[number]>('Overview');
  const [showClosed, setShowClosed] = useState(false);
  const toggleCopilot = useUiStore((s) => s.toggleCopilotPanel);
  const {
    summary,
    positions,
    performance,
    attribution,
    reconciliationBlocked,
    isLoading,
    isError,
    error,
    refetch,
  } = usePortfolioScreen(showClosed);
  const { returnSeries, navSeries } = useNavHistory();

  const allocation = positions
    .filter((p) => (p.weight_pct ?? 0) > 0)
    .map((p) => ({ label: p.symbol ?? '—', value: p.weight_pct ?? 0 }));

  const sectorMap = new Map<string, number>();
  for (const p of positions) {
    const sector = p.sector ?? 'Other';
    sectorMap.set(sector, (sectorMap.get(sector) ?? 0) + (p.weight_pct ?? 0));
  }
  const sectorExposure = [...sectorMap.entries()].map(([label, value]) => ({ label, value }));

  return (
    <InvestorScreenShell
      title="Portfolio"
      subtitle="Positions · Allocation · Performance · Risk"
      headerRight={<Button label="Copilot" onPress={toggleCopilot} variant="ghost" />}
    >
      <View style={styles.tabs}>
        {TABS.map((t) => (
          <Pressable
            key={t}
            onPress={() => setSection(t)}
            style={[
              styles.tab,
              {
                backgroundColor: section === t ? theme.colors.sidebarActive : theme.colors.backgroundPanel,
                borderColor: theme.colors.border,
              },
            ]}
          >
            <Text style={[styles.tabText, { color: section === t ? theme.colors.accent : theme.colors.textMuted }]}>
              {t}
            </Text>
          </Pressable>
        ))}
      </View>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorState
          message={error instanceof Error ? error.message : 'Failed to load portfolio'}
          onRetry={() => void refetch()}
        />
      )}

      {section === 'Overview' && summary && (
        <View style={[styles.summary, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border }]}>
          <View style={styles.summaryRow}>
            <View>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>EQUITY</Text>
              <MetricValue value={summary.total_equity} format="currency" size="lg" />
            </View>
            <View>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>CASH</Text>
              <MetricValue value={summary.cash_pct} format="percent" />
            </View>
            <View>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>DEPLOYABLE</Text>
              <MetricValue value={summary.deployable_capital} format="currency" />
            </View>
            <View>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>UNREALIZED P&L</Text>
              <MetricValue value={summary.unrealized_pnl} format="currency" colorize />
            </View>
          </View>
          <Text style={[styles.posture, { color: theme.colors.textSecondary }]}>
            {summary.regime_posture} · {summary.active_positions} positions · {summary.slots_available} slots
          </Text>
        </View>
      )}

      {section === 'Positions' && (
        <View style={styles.list}>
          {/* Open / Closed toggle */}
          <View style={styles.toggleRow}>
            <Pressable
              onPress={() => setShowClosed(false)}
              style={[
                styles.toggleBtn,
                {
                  backgroundColor: !showClosed ? theme.colors.accent : theme.colors.backgroundPanel,
                  borderColor: theme.colors.border,
                },
              ]}
            >
              <Text style={[styles.toggleText, { color: !showClosed ? '#fff' : theme.colors.textMuted }]}>
                Open ({positions.filter((p) => p.position_status === 'OPEN').length})
              </Text>
            </Pressable>
            <Pressable
              onPress={() => setShowClosed(true)}
              style={[
                styles.toggleBtn,
                {
                  backgroundColor: showClosed ? theme.colors.accent : theme.colors.backgroundPanel,
                  borderColor: theme.colors.border,
                },
              ]}
            >
              <Text style={[styles.toggleText, { color: showClosed ? '#fff' : theme.colors.textMuted }]}>
                Exited ({positions.filter((p) => p.position_status === 'CLOSED').length})
              </Text>
            </Pressable>
          </View>

          {positions
            .filter((p) => showClosed ? p.position_status === 'CLOSED' : p.position_status === 'OPEN')
            .map((p) => (
              <PortfolioPositionCard
                key={p.id}
                symbol={p.symbol}
                quantity={p.quantity}
                avgCost={p.avg_cost}
                marketValue={p.market_value}
                unrealizedPnl={p.unrealized_pnl}
                weightPct={p.weight_pct}
                convictionBand={p.conviction_band}
                sector={p.sector}
                positionStatus={p.position_status}
                exitPrice={p.exit_price}
                exitDate={p.exit_date}
                realizedPnl={p.realized_pnl}
                entryDate={p.entry_date}
                strategyName={p.strategy_name}
              />
            ))}

          {positions.filter((p) => showClosed ? p.position_status === 'CLOSED' : p.position_status === 'OPEN').length === 0 && (
            <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>
              {showClosed ? 'No exited positions yet.' : 'No open positions.'}
            </Text>
          )}
        </View>
      )}

      {section === 'Allocation' && (
        <View style={[styles.chartBox, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
          <DonutChart segments={allocation} />
          <Text style={[styles.chartTitle, { color: theme.colors.textMuted }]}>SECTOR EXPOSURE</Text>
          <BarChart items={sectorExposure.map((s) => ({ label: s.label, value: s.value }))} />
        </View>
      )}

      {section === 'Performance' && performance && (
        <View style={styles.perfSection}>
          <View style={styles.perfRow}>
            <MetricValue value={performance.total_return_pct} format="percent" colorize size="lg" />
            <Text style={[styles.perfLabel, { color: theme.colors.textMuted }]}>Total return</Text>
            <MetricValue value={performance.alpha_pct} format="percent" colorize />
            <Text style={[styles.perfLabel, { color: theme.colors.textMuted }]}>Alpha</Text>
            <MetricValue value={performance.sharpe_ratio} format="number" />
            <Text style={[styles.perfLabel, { color: theme.colors.textMuted }]}>Sharpe</Text>
          </View>
          <SparklineChart data={returnSeries.length > 1 ? returnSeries : navSeries} emptyLabel="Building performance history" />
        </View>
      )}

      {section === 'Attribution' && (
        reconciliationBlocked ? (
          <Text style={[styles.gate, { color: theme.colors.warning }]}>
            Attribution unavailable — portfolio reconciliation must pass first.
          </Text>
        ) : attribution ? (
          <BarChart
            items={attribution.by_sector.map((b) => ({
              label: b.label,
              value: b.contribution_pct,
            }))}
            emptyLabel="No attribution data"
          />
        ) : null
      )}
    </InvestorScreenShell>
  );
}

const styles = StyleSheet.create({
  tabs: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  tab: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  tabText: {
    fontSize: 11,
    fontWeight: '600',
  },
  summary: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 16,
    gap: 8,
  },
  summaryRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 20,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  posture: {
    fontSize: 12,
  },
  list: {
    gap: 10,
  },
  toggleRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 4,
  },
  toggleBtn: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 14,
    paddingVertical: 7,
  },
  toggleText: {
    fontSize: 12,
    fontWeight: '600',
  },
  emptyText: {
    fontSize: 13,
    textAlign: 'center',
    paddingVertical: 24,
  },
  chartBox: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 16,
    gap: 12,
  },
  chartTitle: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  perfSection: {
    gap: 12,
  },
  perfRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 8,
  },
  perfLabel: {
    fontSize: 11,
    marginRight: 12,
  },
  gate: {
    fontSize: 13,
    padding: 12,
  },
});
