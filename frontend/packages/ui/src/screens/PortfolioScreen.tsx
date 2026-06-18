import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable, TextInput } from 'react-native';
import { useTheme, useBreakpoint } from '@pipm/theme';
import { usePortfolioScreen, useNavHistory, useUiStore } from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { LoadingState } from '../feedback/LoadingState';
import { ErrorState } from '../feedback/ErrorState';
import { MetricValue } from '../atoms/MetricValue';
import { PortfolioPositionCard } from '../molecules/PortfolioPositionCard';
import { SectorPieCard } from '../molecules/SectorPieCard';
import { ConcentrationCard } from '../molecules/ConcentrationCard';
import { PositionPnlCard } from '../molecules/PositionPnlCard';
import { ConvictionMixCard } from '../molecules/ConvictionMixCard';
import { SparklineChart } from '../charts/SparklineChart';
import { DonutChart } from '../charts/DonutChart';
import { BarChart } from '../charts/BarChart';
import { Button } from '../atoms/Button';

const TABS = ['Overview', 'Positions', 'Allocation', 'Performance', 'Attribution'] as const;

const EXIT_REASONS = ['STOP_LOSS', 'TIME_STOP', 'RANK_DROP', 'FORCE_CLOSE'] as const;

export function PortfolioScreen() {
  const theme = useTheme();
  const { isDesktop } = useBreakpoint();
  const [section, setSection] = useState<(typeof TABS)[number]>('Overview');
  const [showClosed, setShowClosed] = useState(false);

  // Filter state — Open tab
  const [filterStrategy, setFilterStrategy] = useState<string | null>(null);
  const [filterSector, setFilterSector] = useState<string | null>(null);

  // Filter state — Closed tab
  const [filterClosedStrategy, setFilterClosedStrategy] = useState<string | null>(null);
  const [filterClosedSector, setFilterClosedSector] = useState<string | null>(null);
  const [filterExitReason, setFilterExitReason] = useState<string | null>(null);
  const [filterPnlDir, setFilterPnlDir] = useState<'All' | 'Winners' | 'Losers'>('All');

  // Search state — Open tab
  const [searchOpen, setSearchOpen] = useState('');
  const [openFromDate, setOpenFromDate] = useState('');
  const [openToDate, setOpenToDate] = useState('');

  // Search state — Closed tab
  const [searchClosed, setSearchClosed] = useState('');
  const [closedFromDate, setClosedFromDate] = useState('');
  const [closedToDate, setClosedToDate] = useState('');

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
  const { points, returnSeries, navSeries } = useNavHistory();

  // Derive unique filter options from loaded positions
  const openPositions = positions.filter((p) => p.position_status === 'OPEN');
  const closedPositions = positions.filter((p) => p.position_status === 'CLOSED');

  const openStrategies = [...new Set(openPositions.map((p) => p.strategy_name).filter(Boolean))];
  const openSectors = [...new Set(openPositions.map((p) => p.sector).filter(Boolean))];
  const closedStrategies = [...new Set(closedPositions.map((p) => p.strategy_name).filter(Boolean))];
  const closedSectors = [...new Set(closedPositions.map((p) => p.sector).filter(Boolean))];

  const filteredOpen = openPositions.filter((p) => {
    if (filterStrategy && p.strategy_name !== filterStrategy) return false;
    if (filterSector && p.sector !== filterSector) return false;
    if (searchOpen && !(p.symbol ?? '').toLowerCase().includes(searchOpen.toLowerCase())) return false;
    const entryD = p.entry_date ? p.entry_date.slice(0, 10) : '';
    if (openFromDate && entryD < openFromDate) return false;
    if (openToDate && entryD > openToDate) return false;
    return true;
  });

  const filteredClosed = closedPositions.filter((p) => {
    if (filterClosedStrategy && p.strategy_name !== filterClosedStrategy) return false;
    if (filterClosedSector && p.sector !== filterClosedSector) return false;
    if (filterExitReason && p.exit_reason !== filterExitReason) return false;
    if (filterPnlDir === 'Winners' && (p.realized_pnl ?? 0) <= 0) return false;
    if (filterPnlDir === 'Losers' && (p.realized_pnl ?? 0) >= 0) return false;
    if (searchClosed && !(p.symbol ?? '').toLowerCase().includes(searchClosed.toLowerCase())) return false;
    const exitD = p.exit_date ? p.exit_date.slice(0, 10) : '';
    if (closedFromDate && exitD < closedFromDate) return false;
    if (closedToDate && exitD > closedToDate) return false;
    return true;
  });

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
              {/* summary.cash_pct is a 0–1 fraction; the percent formatter expects
                  a 0–100 number (as the dashboard endpoint already returns). */}
              <MetricValue value={summary.cash_pct == null ? null : summary.cash_pct * 100} format="percent" />
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

      {section === 'Overview' && (
        <View style={[styles.analyticsGrid, !isDesktop && styles.analyticsGridStack]}>
          <View style={isDesktop ? styles.gridItem : undefined}>
            <SectorPieCard positions={positions} />
          </View>
          <View style={isDesktop ? styles.gridItem : undefined}>
            <ConvictionMixCard positions={positions} />
          </View>
          <View style={isDesktop ? styles.gridItem : undefined}>
            <ConcentrationCard positions={positions} />
          </View>
          <View style={isDesktop ? styles.gridItem : undefined}>
            <PositionPnlCard positions={positions} />
          </View>
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
                Open ({openPositions.length})
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
                Exited ({closedPositions.length})
              </Text>
            </Pressable>
          </View>

          {/* ── Search bar for Open positions ── */}
          {!showClosed && (
            <View style={styles.searchSection}>
              <TextInput
                style={[styles.searchInput, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border, color: theme.colors.textPrimary }]}
                placeholder="Search symbol…"
                placeholderTextColor={theme.colors.textMuted}
                value={searchOpen}
                onChangeText={setSearchOpen}
                autoCapitalize="characters"
                autoCorrect={false}
              />
              <View style={styles.dateRow}>
                <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>Entry</Text>
                <TextInput
                  style={[styles.dateInput, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border, color: theme.colors.textPrimary }]}
                  placeholder="From YYYY-MM-DD"
                  placeholderTextColor={theme.colors.textMuted}
                  value={openFromDate}
                  onChangeText={setOpenFromDate}
                  autoCorrect={false}
                />
                <TextInput
                  style={[styles.dateInput, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border, color: theme.colors.textPrimary }]}
                  placeholder="To YYYY-MM-DD"
                  placeholderTextColor={theme.colors.textMuted}
                  value={openToDate}
                  onChangeText={setOpenToDate}
                  autoCorrect={false}
                />
                {(searchOpen || openFromDate || openToDate) && (
                  <Pressable onPress={() => { setSearchOpen(''); setOpenFromDate(''); setOpenToDate(''); }}>
                    <Text style={[styles.clearBtn, { color: theme.colors.accent }]}>Clear</Text>
                  </Pressable>
                )}
              </View>
            </View>
          )}

          {/* ── Filters for Open positions ── */}
          {!showClosed && (openStrategies.length > 0 || openSectors.length > 0) && (
            <View style={styles.filterSection}>
              {openStrategies.length > 0 && (
                <View style={styles.filterRow}>
                  <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>Strategy</Text>
                  <Pressable
                    onPress={() => setFilterStrategy(null)}
                    style={[styles.chip, { backgroundColor: filterStrategy === null ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                  >
                    <Text style={[styles.chipText, { color: filterStrategy === null ? '#fff' : theme.colors.textMuted }]}>All</Text>
                  </Pressable>
                  {openStrategies.map((s) => (
                    <Pressable
                      key={s}
                      onPress={() => setFilterStrategy(filterStrategy === s ? null : s)}
                      style={[styles.chip, { backgroundColor: filterStrategy === s ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                    >
                      <Text style={[styles.chipText, { color: filterStrategy === s ? '#fff' : theme.colors.textMuted }]}>
                        {(s ?? '').replace('_v1', '')}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              )}
              {openSectors.length > 0 && (
                <View style={styles.filterRow}>
                  <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>Sector</Text>
                  <Pressable
                    onPress={() => setFilterSector(null)}
                    style={[styles.chip, { backgroundColor: filterSector === null ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                  >
                    <Text style={[styles.chipText, { color: filterSector === null ? '#fff' : theme.colors.textMuted }]}>All</Text>
                  </Pressable>
                  {openSectors.map((s) => (
                    <Pressable
                      key={s}
                      onPress={() => setFilterSector(filterSector === s ? null : s)}
                      style={[styles.chip, { backgroundColor: filterSector === s ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                    >
                      <Text style={[styles.chipText, { color: filterSector === s ? '#fff' : theme.colors.textMuted }]}>{s}</Text>
                    </Pressable>
                  ))}
                </View>
              )}
            </View>
          )}

          {/* ── Search bar for Closed positions ── */}
          {showClosed && (
            <View style={styles.searchSection}>
              <TextInput
                style={[styles.searchInput, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border, color: theme.colors.textPrimary }]}
                placeholder="Search symbol…"
                placeholderTextColor={theme.colors.textMuted}
                value={searchClosed}
                onChangeText={setSearchClosed}
                autoCapitalize="characters"
                autoCorrect={false}
              />
              <View style={styles.dateRow}>
                <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>Exit</Text>
                <TextInput
                  style={[styles.dateInput, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border, color: theme.colors.textPrimary }]}
                  placeholder="From YYYY-MM-DD"
                  placeholderTextColor={theme.colors.textMuted}
                  value={closedFromDate}
                  onChangeText={setClosedFromDate}
                  autoCorrect={false}
                />
                <TextInput
                  style={[styles.dateInput, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border, color: theme.colors.textPrimary }]}
                  placeholder="To YYYY-MM-DD"
                  placeholderTextColor={theme.colors.textMuted}
                  value={closedToDate}
                  onChangeText={setClosedToDate}
                  autoCorrect={false}
                />
                {(searchClosed || closedFromDate || closedToDate) && (
                  <Pressable onPress={() => { setSearchClosed(''); setClosedFromDate(''); setClosedToDate(''); }}>
                    <Text style={[styles.clearBtn, { color: theme.colors.accent }]}>Clear</Text>
                  </Pressable>
                )}
              </View>
            </View>
          )}

          {/* ── Filters for Closed positions ── */}
          {showClosed && (
            <View style={styles.filterSection}>
              {closedStrategies.length > 0 && (
                <View style={styles.filterRow}>
                  <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>Strategy</Text>
                  <Pressable
                    onPress={() => setFilterClosedStrategy(null)}
                    style={[styles.chip, { backgroundColor: filterClosedStrategy === null ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                  >
                    <Text style={[styles.chipText, { color: filterClosedStrategy === null ? '#fff' : theme.colors.textMuted }]}>All</Text>
                  </Pressable>
                  {closedStrategies.map((s) => (
                    <Pressable
                      key={s}
                      onPress={() => setFilterClosedStrategy(filterClosedStrategy === s ? null : s)}
                      style={[styles.chip, { backgroundColor: filterClosedStrategy === s ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                    >
                      <Text style={[styles.chipText, { color: filterClosedStrategy === s ? '#fff' : theme.colors.textMuted }]}>
                        {(s ?? '').replace('_v1', '')}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              )}
              {closedSectors.length > 0 && (
                <View style={styles.filterRow}>
                  <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>Sector</Text>
                  <Pressable
                    onPress={() => setFilterClosedSector(null)}
                    style={[styles.chip, { backgroundColor: filterClosedSector === null ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                  >
                    <Text style={[styles.chipText, { color: filterClosedSector === null ? '#fff' : theme.colors.textMuted }]}>All</Text>
                  </Pressable>
                  {closedSectors.map((s) => (
                    <Pressable
                      key={s}
                      onPress={() => setFilterClosedSector(filterClosedSector === s ? null : s)}
                      style={[styles.chip, { backgroundColor: filterClosedSector === s ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                    >
                      <Text style={[styles.chipText, { color: filterClosedSector === s ? '#fff' : theme.colors.textMuted }]}>{s}</Text>
                    </Pressable>
                  ))}
                </View>
              )}
              <View style={styles.filterRow}>
                <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>Exit Reason</Text>
                <Pressable
                  onPress={() => setFilterExitReason(null)}
                  style={[styles.chip, { backgroundColor: filterExitReason === null ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                >
                  <Text style={[styles.chipText, { color: filterExitReason === null ? '#fff' : theme.colors.textMuted }]}>All</Text>
                </Pressable>
                {EXIT_REASONS.map((r) => (
                  <Pressable
                    key={r}
                    onPress={() => setFilterExitReason(filterExitReason === r ? null : r)}
                    style={[styles.chip, { backgroundColor: filterExitReason === r ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                  >
                    <Text style={[styles.chipText, { color: filterExitReason === r ? '#fff' : theme.colors.textMuted }]}>
                      {r.replace('_', ' ')}
                    </Text>
                  </Pressable>
                ))}
              </View>
              <View style={styles.filterRow}>
                <Text style={[styles.filterLabel, { color: theme.colors.textMuted }]}>P&L</Text>
                {(['All', 'Winners', 'Losers'] as const).map((d) => (
                  <Pressable
                    key={d}
                    onPress={() => setFilterPnlDir(d)}
                    style={[styles.chip, { backgroundColor: filterPnlDir === d ? theme.colors.accent : theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
                  >
                    <Text style={[styles.chipText, { color: filterPnlDir === d ? '#fff' : theme.colors.textMuted }]}>{d}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          )}

          {(showClosed ? filteredClosed : filteredOpen).map((p) => (
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
              entryPrice={p.entry_price}
              strategyName={p.strategy_name}
              exitReason={p.exit_reason}
              ltp={p.ltp}
            />
          ))}

          {(showClosed ? filteredClosed : filteredOpen).length === 0 && (
            <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>
              {showClosed ? 'No exited positions match filters.' : 'No open positions match filters.'}
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
          <SparklineChart
            data={navSeries}
            dates={points.map((p) => p.as_of_date)}
            height={160}
            showScale
            emptyLabel="Building performance history"
          />
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
  analyticsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginTop: 12,
  },
  analyticsGridStack: {
    flexDirection: 'column',
  },
  gridItem: {
    flexGrow: 1,
    flexBasis: '48%',
    minWidth: 320,
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
  filterSection: {
    gap: 6,
  },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 6,
  },
  filterLabel: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginRight: 2,
    minWidth: 60,
  },
  chip: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  chipText: {
    fontSize: 11,
    fontWeight: '500',
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
  searchSection: {
    gap: 6,
  },
  searchInput: {
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 7,
    fontSize: 13,
  },
  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  dateInput: {
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 6,
    fontSize: 12,
    flex: 1,
    minWidth: 120,
  },
  clearBtn: {
    fontSize: 12,
    fontWeight: '600',
    paddingHorizontal: 4,
  },
});
