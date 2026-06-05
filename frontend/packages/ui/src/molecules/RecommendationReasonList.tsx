import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Badge } from '../atoms/Badge';

export interface RecommendationReasonListProps {
  reasonCodes: string[];
  maxVisible?: number;
  direction?: 'horizontal' | 'vertical';
}

const REASON_LABELS: Record<string, string> = {
  RANK_TOP_20: 'Top 20',
  VALIDATION_PASS: 'Validated',
  REGIME_RISK_ON: 'Risk-on',
  EXIT_TRIGGER_RANK: 'Rank exit',
};

export function RecommendationReasonList({
  reasonCodes,
  maxVisible = 4,
  direction = 'horizontal',
}: RecommendationReasonListProps) {
  const visible = reasonCodes.slice(0, maxVisible);
  const overflow = reasonCodes.length - visible.length;

  return (
    <View
      style={[
        styles.container,
        direction === 'horizontal' ? styles.horizontal : styles.vertical,
      ]}
    >
      {visible.map((code) => (
        <Badge key={code} label={REASON_LABELS[code] ?? code} variant="info" size="sm" />
      ))}
      {overflow > 0 && <Badge label={`+${overflow}`} variant="default" size="sm" />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 4,
  },
  horizontal: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  vertical: {
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
});
