import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { RecommendationExecutionContext } from '@pipm/types';
import { Badge } from '../atoms/Badge';
import { PortfolioPositionCard } from './PortfolioPositionCard';

export interface RecommendationExecutionPanelProps {
  lifecycleState: string | null;
  execution: RecommendationExecutionContext | null;
  symbol: string;
}

function approvalBadges(execution: RecommendationExecutionContext | null) {
  const approvals = execution?.approvals ?? [];
  if (!approvals.length) return [];
  return approvals.map((a) => ({
    key: `${a.approval_type}-${a.decision}`,
    label: `${a.approval_type} ${a.decision}`,
    variant: a.decision === 'APPROVED' ? ('success' as const) : ('danger' as const),
  }));
}

function tradeBadges(execution: RecommendationExecutionContext | null) {
  const trades = execution?.trades ?? [];
  if (!trades.length) return [];
  return trades.map((t, i) => ({
    key: `trade-${i}`,
    label: `${t.side} @ ${Number(t.fill_price).toFixed(2)}`,
    variant: t.side === 'BUY' ? ('success' as const) : ('danger' as const),
  }));
}

export function RecommendationExecutionPanel({
  lifecycleState,
  execution,
  symbol,
}: RecommendationExecutionPanelProps) {
  const theme = useTheme();
  const badges = [
    ...(lifecycleState ? [{ key: 'life', label: lifecycleState, variant: 'info' as const }] : []),
    ...approvalBadges(execution),
    ...tradeBadges(execution),
  ];
  const position = execution?.position;
  const outcome = execution?.outcome;
  const hasDetail = badges.length > 0 || !!position || !!outcome;

  if (!hasDetail) {
    return (
      <Text style={[styles.empty, { color: theme.colors.textMuted }]}>
        No execution history for {symbol} on this day.
      </Text>
    );
  }

  return (
    <View style={styles.panel} accessibilityLabel={`Execution history for ${symbol}`}>
      {badges.length > 0 && (
        <View style={styles.badges}>
          {badges.map((b) => (
            <Badge key={b.key} label={b.label} variant={b.variant} size="sm" />
          ))}
        </View>
      )}

      {outcome && (
        <View style={styles.metaRow}>
          <Text style={[styles.meta, { color: theme.colors.textMuted }]}>
            Outcome: {outcome.outcome_status}
            {outcome.pnl_pct != null ? ` · ${outcome.pnl_pct.toFixed(1)}%` : ''}
            {outcome.days_held != null ? ` · ${outcome.days_held}d` : ''}
            {outcome.exit_reason ? ` · ${outcome.exit_reason}` : ''}
          </Text>
        </View>
      )}

      {position && (
        <PortfolioPositionCard
          symbol={position.symbol ?? symbol}
          quantity={position.quantity}
          avgCost={position.avg_cost}
          entryPrice={position.entry_price}
          marketValue={position.market_value}
          unrealizedPnl={position.unrealized_pnl}
          weightPct={position.weight_pct}
          convictionBand={position.conviction_band}
          sector={position.sector}
          positionStatus={position.position_status as 'OPEN' | 'CLOSED'}
          exitPrice={position.exit_price}
          exitDate={position.exit_date}
          realizedPnl={position.realized_pnl}
          entryDate={position.entry_date}
          strategyName={position.strategy_name}
          exitReason={outcome?.exit_reason ?? null}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    gap: 10,
    paddingTop: 4,
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  metaRow: {
    gap: 4,
  },
  meta: {
    fontSize: 11,
  },
  empty: {
    fontSize: 12,
    fontStyle: 'italic',
  },
});
