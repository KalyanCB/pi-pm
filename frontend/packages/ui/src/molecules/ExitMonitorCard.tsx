import React, { useState } from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { ExitRecommendation } from '@pipm/types';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { MetricValue } from '../atoms/MetricValue';

export interface ExitMonitorCardProps {
  /** Primary (highest urgency) recommendation — drives the master card. */
  exit: ExitRecommendation;
  /** All recs for the same position (including exit itself). */
  allTiers?: ExitRecommendation[];
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

function tierLabel(tier: string) {
  return tier === 'INTRADAY' ? 'T1 · INTRADAY' : 'T2 · DAILY';
}

/** Deduplicated union of all triggers across tiers. */
function mergedTriggers(recs: ExitRecommendation[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const r of recs) {
    for (const t of r.triggers ?? []) {
      if (!seen.has(t)) { seen.add(t); out.push(t); }
    }
  }
  return out;
}

/** Pick the highest urgency across tiers. */
function topUrgency(recs: ExitRecommendation[]): string {
  const order = ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'];
  return recs.reduce((best, r) =>
    order.indexOf(r.urgency) > order.indexOf(best) ? r.urgency : best,
    'LOW');
}

export function ExitMonitorCard({
  exit,
  allTiers,
  onConfirm,
  onReject,
  confirming = false,
  rejecting = false,
}: ExitMonitorCardProps) {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);

  const tiers = allTiers && allTiers.length > 0 ? allTiers : [exit];
  const isPending = tiers.some((r) => r.status === 'PENDING');
  const canAct = isPending && !!onConfirm && !!onReject;
  const urgency = topUrgency(tiers);
  const triggers = mergedTriggers(tiers);
  const hasMultipleTiers = tiers.length > 1;

  // Best context values from any tier
  const current_rank = tiers.map((r) => r.current_rank).find((v) => v != null);
  const days_held = tiers.map((r) => r.days_held).find((v) => v != null);
  const unrealized_pnl_pct = tiers.map((r) => r.unrealized_pnl_pct).find((v) => v != null);

  return (
    <View style={[styles.card, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
      {/* ── Master header ── */}
      <View style={styles.header}>
        <Text style={[styles.symbol, { color: theme.colors.textPrimary }]}>{exit.symbol ?? '—'}</Text>
        <Badge label="EXIT MONITOR" variant="danger" size="sm" />
        <Badge label={isPending ? 'PENDING' : exit.status} variant={isPending ? 'warning' : 'default'} size="sm" />
        <Badge label={urgency} variant={urgencyVariant(urgency)} size="sm" />
        {hasMultipleTiers && (
          <Badge label={`${tiers.length} tiers`} variant="info" size="sm" />
        )}
      </View>

      {/* ── Merged triggers ── */}
      <View style={styles.triggers}>
        {triggers.map((t) => (
          <Badge key={t} label={t} variant="info" size="sm" />
        ))}
      </View>

      {/* ── Metrics ── */}
      <View style={styles.metrics}>
        {current_rank != null && (
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Rank</Text>
            <MetricValue value={current_rank} format="integer" size="sm" />
          </View>
        )}
        {days_held != null && (
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Held</Text>
            <Text style={[styles.mono, { color: theme.colors.textSecondary }]}>{days_held}d</Text>
          </View>
        )}
        {unrealized_pnl_pct != null && (
          <View style={styles.metric}>
            <Text style={[styles.label, { color: theme.colors.textMuted }]}>Unrealized</Text>
            <MetricValue value={unrealized_pnl_pct} format="percent" colorize size="sm" />
          </View>
        )}
      </View>

      {/* ── Tier detail (expandable) ── */}
      {hasMultipleTiers && (
        <>
          <Pressable onPress={() => setExpanded((e) => !e)} style={styles.tierToggle}>
            <Text style={[styles.tierToggleText, { color: theme.colors.accent }]}>
              {expanded ? '▲ Hide tier detail' : `▼ Show tier detail (${tiers.length})`}
            </Text>
          </Pressable>
          {expanded && (
            <View style={[styles.tierDetail, { borderColor: theme.colors.border }]}>
              {tiers.map((r) => (
                <View key={r.id} style={styles.tierRow}>
                  <View style={styles.tierRowHeader}>
                    <Text style={[styles.tierLabel, { color: theme.colors.textMuted }]}>
                      {tierLabel(r.monitor_tier ?? 'DAILY')}
                    </Text>
                    <Badge label={r.urgency} variant={urgencyVariant(r.urgency)} size="sm" />
                    <Badge label={r.status} variant={r.status === 'PENDING' ? 'warning' : 'default'} size="sm" />
                  </View>
                  <View style={styles.tierTriggers}>
                    {(r.triggers ?? []).map((t) => (
                      <Badge key={t} label={t} variant="info" size="sm" />
                    ))}
                  </View>
                </View>
              ))}
            </View>
          )}
        </>
      )}

      {/* ── Actions ── */}
      {canAct && (
        <View style={styles.actions}>
          <Button label="Confirm exit" variant="danger" onPress={onConfirm} loading={confirming} />
          <Button label="Defer" variant="ghost" onPress={onReject} loading={rejecting} />
        </View>
      )}

      {!isPending && (
        <Text style={[styles.resolved, { color: theme.colors.textMuted }]}>
          {tiers.some((r) => r.status === 'CONFIRMED')
            ? 'Exit confirmed and executed.'
            : 'Exit deferred or rejected.'}
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
  tierToggle: {
    paddingVertical: 2,
  },
  tierToggleText: {
    fontSize: 11,
    fontWeight: '600',
  },
  tierDetail: {
    borderWidth: 1,
    borderRadius: 4,
    padding: 8,
    gap: 8,
  },
  tierRow: {
    gap: 4,
  },
  tierRowHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  tierLabel: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  tierTriggers: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    paddingLeft: 4,
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
