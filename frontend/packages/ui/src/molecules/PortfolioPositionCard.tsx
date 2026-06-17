import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { PortfolioPositionCardProps } from '@pipm/types';
import { MetricValue } from '../atoms/MetricValue';
import { Badge } from '../atoms/Badge';

function fmt(v: number | null | undefined, decimals = 2): string {
  if (v == null) return '—';
  return `₹${Number(v).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
}

function fmtPct(v: number | null | undefined): { text: string; positive: boolean | null } {
  if (v == null) return { text: '—', positive: null };
  const sign = v > 0 ? '+' : '';
  return { text: `${sign}${v.toFixed(2)}%`, positive: v > 0 ? true : v < 0 ? false : null };
}

export function PortfolioPositionCard({
  symbol,
  quantity,
  avgCost,
  marketValue,
  unrealizedPnl,
  weightPct,
  convictionBand,
  sector,
  onPress,
  positionStatus,
  exitPrice,
  exitDate,
  realizedPnl,
  entryDate,
  entryPrice,
  strategyName,
  exitReason,
}: PortfolioPositionCardProps) {
  const theme = useTheme();
  const isClosed = positionStatus === 'CLOSED';

  // Derived values
  const investedPerShare = avgCost ?? entryPrice;
  const currentPrice = marketValue != null && quantity > 0 ? marketValue / quantity : null;
  const unrealizedPct =
    investedPerShare != null && investedPerShare > 0 && currentPrice != null
      ? ((currentPrice - investedPerShare) / investedPerShare) * 100
      : null;
  const realizedPct =
    entryPrice != null && entryPrice > 0 && exitPrice != null
      ? ((exitPrice - entryPrice) / entryPrice) * 100
      : null;

  const pnlColor = (pos: boolean | null) =>
    pos === true ? theme.colors.positive : pos === false ? theme.colors.negative : theme.colors.textSecondary;

  const content = (
    <View
      style={[
        styles.card,
        {
          backgroundColor: isClosed ? theme.colors.backgroundPanel : theme.colors.backgroundElevated,
          borderColor: theme.colors.border,
          opacity: isClosed ? 0.85 : 1,
        },
      ]}
    >
      {/* ── Header ── */}
      <View style={styles.header}>
        <Text style={[styles.symbol, { color: isClosed ? theme.colors.textMuted : theme.colors.textPrimary }]}>
          {symbol ?? '—'}
        </Text>
        {isClosed ? (
          <Badge label="EXITED" variant="default" size="sm" />
        ) : (
          convictionBand && <Badge label={convictionBand} variant="info" size="sm" />
        )}
        {strategyName && (
          <Text style={[styles.chip, { color: theme.colors.textMuted }]}>
            {strategyName.replace('_v1', '')}
          </Text>
        )}
        {sector && (
          <Text style={[styles.chip, { color: theme.colors.textMuted, marginLeft: 'auto' }]}>{sector}</Text>
        )}
      </View>

      {isClosed ? (
        // ── Closed: highlight return % alongside realized P&L ──
        <>
          <View style={styles.primaryRow}>
            {/* Realized P&L ₹ */}
            <View style={styles.primaryBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Realized P&L</Text>
              <MetricValue value={realizedPnl ?? null} format="currency" colorize size="sm" />
            </View>
            {/* Return % */}
            {realizedPct != null && (
              <View style={styles.primaryBlock}>
                <Text style={[styles.label, { color: theme.colors.textMuted }]}>Return</Text>
                <Text style={[styles.bigPct, { color: pnlColor(realizedPct > 0 ? true : realizedPct < 0 ? false : null) }]}>
                  {fmtPct(realizedPct).text}
                </Text>
              </View>
            )}
            {/* Qty */}
            <View style={styles.primaryBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Qty</Text>
              <MetricValue value={quantity} format="number" size="sm" />
            </View>
          </View>

          {/* Price row: entry → exit */}
          <View style={styles.priceRow}>
            <View style={styles.priceBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Invested</Text>
              <Text style={[styles.price, { color: theme.colors.textSecondary }]}>
                {fmt(investedPerShare)}
              </Text>
            </View>
            <Text style={[styles.arrow, { color: theme.colors.textMuted }]}>→</Text>
            <View style={styles.priceBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Exited</Text>
              <Text style={[styles.price, { color: theme.colors.textSecondary }]}>
                {fmt(exitPrice)}
              </Text>
            </View>
            {exitReason && (
              <View style={[styles.priceBlock, { marginLeft: 'auto' }]}>
                <Text style={[styles.label, { color: theme.colors.textMuted }]}>Reason</Text>
                <Text style={[styles.reasonText, { color: theme.colors.textMuted }]}>
                  {exitReason.replace(/_/g, ' ')}
                </Text>
              </View>
            )}
          </View>
        </>
      ) : (
        // ── Open: highlight market value + unrealized P&L % ──
        <>
          <View style={styles.primaryRow}>
            {/* Market value */}
            <View style={styles.primaryBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Value</Text>
              <MetricValue value={marketValue} format="currency" size="sm" />
            </View>
            {/* Unrealized P&L ₹ */}
            <View style={styles.primaryBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Unrealized P&L</Text>
              <MetricValue value={unrealizedPnl} format="currency" colorize size="sm" />
            </View>
            {/* P&L % */}
            {unrealizedPct != null && (
              <View style={styles.primaryBlock}>
                <Text style={[styles.label, { color: theme.colors.textMuted }]}>P&L %</Text>
                <Text style={[styles.bigPct, { color: pnlColor(unrealizedPct > 0 ? true : unrealizedPct < 0 ? false : null) }]}>
                  {fmtPct(unrealizedPct).text}
                </Text>
              </View>
            )}
            {/* Weight */}
            <View style={[styles.primaryBlock, { marginLeft: 'auto' }]}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Wt</Text>
              <MetricValue value={weightPct} format="percent" size="sm" />
            </View>
          </View>

          {/* Price row: invested → current */}
          <View style={styles.priceRow}>
            <View style={styles.priceBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Qty</Text>
              <Text style={[styles.price, { color: theme.colors.textSecondary }]}>
                {quantity != null ? quantity.toFixed(2) : '—'}
              </Text>
            </View>
            <View style={styles.priceBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Avg Cost</Text>
              <Text style={[styles.price, { color: theme.colors.textSecondary }]}>
                {fmt(investedPerShare)}
              </Text>
            </View>
            <Text style={[styles.arrow, { color: theme.colors.textMuted }]}>→</Text>
            <View style={styles.priceBlock}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Current</Text>
              <Text style={[styles.price, { color: theme.colors.textPrimary }]}>
                {fmt(currentPrice)}
              </Text>
            </View>
          </View>
        </>
      )}

      {/* ── Date strip ── */}
      <Text style={[styles.dates, { color: theme.colors.textMuted }]}>
        {entryDate ?? ''}
        {isClosed && exitDate ? ` → ${exitDate}` : ''}
      </Text>
    </View>
  );

  if (onPress) {
    return (
      <Pressable onPress={onPress} accessibilityRole="button">
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
  },
  chip: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  primaryRow: {
    flexDirection: 'row',
    gap: 16,
    flexWrap: 'wrap',
    alignItems: 'flex-end',
  },
  primaryBlock: {
    gap: 2,
  },
  bigPct: {
    fontSize: 15,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  priceRow: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  priceBlock: {
    gap: 2,
  },
  label: {
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  price: {
    fontSize: 13,
    fontFamily: 'monospace',
  },
  arrow: {
    fontSize: 14,
    marginTop: 10,
  },
  reasonText: {
    fontSize: 10,
    textTransform: 'uppercase',
  },
  dates: {
    fontSize: 11,
    fontFamily: 'monospace',
  },
});
