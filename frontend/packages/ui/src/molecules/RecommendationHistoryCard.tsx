import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { RecommendationCardProps } from '@pipm/types';
import type { RecommendationExecutionContext } from '@pipm/types';
import { RecommendationCard } from './RecommendationCard';
import { RecommendationExecutionPanel } from './RecommendationExecutionPanel';

export interface RecommendationHistoryCardProps extends RecommendationCardProps {
  lifecycleState?: string | null;
  execution?: RecommendationExecutionContext | null;
  expanded?: boolean;
  onToggleExpand?: () => void;
  hasExecutionHistory?: boolean;
}

export function RecommendationHistoryCard({
  lifecycleState = null,
  execution = null,
  expanded = false,
  onToggleExpand,
  hasExecutionHistory = false,
  onPress,
  ...cardProps
}: RecommendationHistoryCardProps) {
  const theme = useTheme();
  const showExpand = hasExecutionHistory;

  const handleToggleExpand = () => {
    onToggleExpand?.();
  };

  return (
    <View style={[styles.wrap, { borderColor: theme.colors.border }]}>
      <View style={styles.headerRow}>
        <View style={styles.cardTap}>
          <RecommendationCard {...cardProps} layout="card" embedded onPress={onPress} />
        </View>
        {showExpand && onToggleExpand && (
          <Pressable
            onPress={handleToggleExpand}
            style={styles.expandBtn}
            hitSlop={12}
            accessibilityRole="button"
            accessibilityLabel={expanded ? 'Collapse execution history' : 'Expand execution history'}
          >
            <Text style={[styles.expandIcon, { color: theme.colors.accent }]}>
              {expanded ? '▾' : '▸'}
            </Text>
          </Pressable>
        )}
      </View>
      {expanded && showExpand && (
        <View style={[styles.detail, { borderTopColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}>
          <RecommendationExecutionPanel
            lifecycleState={lifecycleState}
            execution={execution}
            symbol={cardProps.symbol}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderRadius: 6,
    overflow: 'visible',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'stretch',
  },
  cardTap: {
    flex: 1,
    minWidth: 0,
  },
  expandBtn: {
    justifyContent: 'center',
    paddingHorizontal: 14,
    minWidth: 40,
  },
  expandIcon: {
    fontSize: 16,
    fontWeight: '700',
  },
  detail: {
    borderTopWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
});
