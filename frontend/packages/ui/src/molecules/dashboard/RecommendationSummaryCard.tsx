import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { MetricCard } from '../../layout/MetricCard';
import { Badge } from '../../atoms/Badge';

export interface RecommendationSummaryCardProps {
  buyCount: number;
  watchCount: number;
  exitCount?: number;
  onPressBuy?: () => void;
  onPressWatch?: () => void;
}

export function RecommendationSummaryCard({
  buyCount,
  watchCount,
  exitCount = 0,
  onPressBuy,
  onPressWatch,
}: RecommendationSummaryCardProps) {
  const theme = useTheme();
  return (
    <MetricCard label="TODAY'S RECOMMENDATIONS" style={{ minWidth: 220, flex: 1 }}>
      <View style={styles.row}>
        <View style={styles.item}>
          <Badge label={`BUY ${buyCount}`} variant="success" />
          {onPressBuy && (
            <Text style={[styles.link, { color: theme.colors.accent }]} onPress={onPressBuy}>
              View →
            </Text>
          )}
        </View>
        <View style={styles.item}>
          <Badge label={`WATCH ${watchCount}`} variant="warning" />
          {onPressWatch && (
            <Text style={[styles.link, { color: theme.colors.accent }]} onPress={onPressWatch}>
              View →
            </Text>
          )}
        </View>
        {exitCount > 0 && <Badge label={`EXIT ${exitCount}`} variant="danger" />}
      </View>
    </MetricCard>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  item: {
    gap: 4,
  },
  link: {
    fontSize: 11,
    fontWeight: '600',
  },
});
