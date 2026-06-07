import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { ExitRecommendation } from '@pipm/types';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { MetricValue } from '../atoms/MetricValue';

export interface ExitMonitorCardProps {
  exit: ExitRecommendation;
  onConfirm?: () => void;
  onReject?: () => void;
  confirming?: boolean;
  rejecting?: boolean;
}

function urgencyVariant(urgency: string): 'default' | 'warning' | 'danger' | 'info' {
  if (urgency === 'CRITICAL' || urgency === 'HIGH') return 'danger';
  if (urgency === 'NORMAL') return 'warning';
  return 'default';
}

export function ExitMonitorCard({
  exit,
  onConfirm,
  onReject,
  confirming = false,
  rejecting = false,
}: ExitMonitorCardProps) {
  const theme = useTheme();
  const isPending = exit.status === 'PENDING';
  const canAct = isPending && !!onConfirm && !!onReject;

  return (
    <View style={[styles.card, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
      <View style={styles.header}>
        <Text style={[styles.symbol, { color: theme.colors.textPrimary }]}>{exit.symbol ?? '—'}</Text>
        <Badge label="EXIT MONITOR" variant="danger" size="sm" />
        <Badge label={exit.status} variant={isPending ? 'warning' : 'default'} size="sm" />
        <Badge label={exit.urgency} variant={urgencyVariant(exit.urgency)} size="sm" />
      </View>

      <View style={styles.triggers}>
        {exit.triggers.map((t) => (
          <Badge key={t} label={t} variant="info" size="sm" />
        ))}
      </View>

      <View style={styles.metrics}>
        {exit.current_rank != null && (
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Rank</Text>
            <MetricValue value={exit.current_rank} format="integer" size="sm" />
          </View>
        )}
        {exit.days_held != null && (
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Held</Text>
            <Text style={[styles.mono, { color: theme.colors.textSecondary }]}>{exit.days_held}d</Text>
          </View>
        )}
        {exit.unrealized_pnl_pct != null && (
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Unrealized</Text>
            <MetricValue value={exit.unrealized_pnl_pct} format="percent" colorize size="sm" />
          </View>
        )}
      </View>

      {canAct && (
        <View style={styles.actions}>
          <Button
            label="Confirm exit"
            variant="danger"
            onPress={onConfirm}
            loading={confirming}
          />
          <Button
            label="Defer"
            variant="ghost"
            onPress={onReject}
            loading={rejecting}
          />
        </View>
      )}

      {!isPending && (
        <Text style={[styles.resolved, { color: theme.colors.textMuted }]}>
          {exit.status === 'CONFIRMED' ? 'Exit confirmed and executed via exit monitor.' : 'Exit deferred or rejected.'}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
  },
  symbol: {
    fontSize: 16,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  triggers: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  metrics: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
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
  actions: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
  },
  resolved: {
    fontSize: 11,
    fontStyle: 'italic',
  },
});
