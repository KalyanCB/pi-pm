import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { PortfolioPositionCardProps } from '@pipm/types';
import { MetricValue } from '../atoms/MetricValue';
import { Badge } from '../atoms/Badge';

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
  // Closed position fields
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

  const content = (
    <View
      style={[
        styles.card,
        {
          backgroundColor: isClosed
            ? theme.colors.backgroundPanel
            : theme.colors.backgroundElevated,
          borderColor: isClosed ? theme.colors.border : theme.colors.border,
          opacity: isClosed ? 0.85 : 1,
        },
      ]}
    >
      <View style={styles.header}>
        <Text style={[styles.symbol, { color: isClosed ? theme.colors.textMuted : theme.colors.textPrimary }]}>
          {symbol ?? '—'}
        </Text>
        {isClosed && (
          <Badge label="EXITED" variant="default" size="sm" />
        )}
        {!isClosed && convictionBand && (
          <Badge label={convictionBand} variant="info" size="sm" />
        )}
        {strategyName && (
          <Text style={[styles.strategy, { color: theme.colors.textMuted }]}>
            {strategyName.replace('_v1', '')}
          </Text>
        )}
        {sector && (
          <Text style={[styles.sector, { color: theme.colors.textMuted }]}>{sector}</Text>
        )}
      </View>

      {isClosed ? (
        // ── Closed position: show entry → exit P&L ──────────────────────────
        <View style={styles.metrics}>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Qty</Text>
            <MetricValue value={quantity} format="number" size="sm" />
          </View>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Entry</Text>
            <Text style={[styles.mono, { color: theme.colors.textSecondary }]}>
              {entryPrice != null ? Number(entryPrice).toFixed(2) : '—'}
            </Text>
          </View>
          <Text style={[styles.arrow, { color: theme.colors.textMuted }]}>→</Text>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Exit</Text>
            <Text style={[styles.mono, { color: theme.colors.textSecondary }]}>
              {exitPrice != null ? exitPrice.toFixed(2) : '—'}
            </Text>
          </View>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Realized P&L</Text>
            <MetricValue value={realizedPnl ?? null} format="currency" colorize size="sm" />
          </View>
          {entryPrice != null && exitPrice != null && (
            <View style={styles.metric}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Return</Text>
              <MetricValue
                value={((exitPrice - entryPrice) / entryPrice) * 100}
                format="percent"
                colorize
                size="sm"
              />
            </View>
          )}
          {exitReason && (
            <View style={styles.metric}>
              <Text style={[styles.label, { color: theme.colors.textMuted }]}>Exit</Text>
              <Text style={[styles.mono, { color: theme.colors.textMuted, fontSize: 11 }]}>
                {exitReason.replace(/_/g, ' ')}
              </Text>
            </View>
          )}
        </View>
      ) : (
        // ── Open position: show live P&L ────────────────────────────────────
        <View style={styles.metrics}>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Qty</Text>
            <MetricValue value={quantity} format="number" size="sm" />
          </View>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Mkt Val</Text>
            <MetricValue value={marketValue} format="currency" size="sm" />
          </View>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Unrealized P&L</Text>
            <MetricValue value={unrealizedPnl} format="currency" colorize size="sm" />
          </View>
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Wt%</Text>
            <MetricValue value={weightPct} format="percent" size="sm" />
          </View>
        </View>
      )}

      <Text style={[styles.dates, { color: theme.colors.textMuted }]}>
        {entryDate ?? ''}
        {isClosed && exitDate ? ` → ${exitDate}` : ''}
        {!isClosed ? `  ·  entry ₹${entryPrice != null ? Number(entryPrice).toFixed(2) : '—'}` : ''}
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
  strategy: {
    fontSize: 10,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  sector: {
    fontSize: 11,
    marginLeft: 'auto',
  },
  metrics: {
    flexDirection: 'row',
    gap: 16,
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  metric: {
    gap: 2,
  },
  label: {
    fontSize: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  mono: {
    fontSize: 13,
    fontFamily: 'monospace',
  },
  arrow: {
    fontSize: 14,
    alignSelf: 'center',
    marginTop: 10,
  },
  dates: {
    fontSize: 11,
    fontFamily: 'monospace',
  },
});
