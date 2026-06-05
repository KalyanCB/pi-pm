import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { ConvictionBand } from '@pipm/types';

export interface ConvictionBadgeProps {
  score: number;
  band: ConvictionBand;
  showScore?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const BAND_COLORS: Record<ConvictionBand, string> = {
  BLOCKED: '#5c6d82',
  LOW: '#8b9cb3',
  MEDIUM: '#5b9bd5',
  HIGH: '#3dba7a',
  EXCEPTIONAL: '#2dd4a8',
};

export function ConvictionBadge({
  score,
  band,
  showScore = true,
  size = 'md',
}: ConvictionBadgeProps) {
  const theme = useTheme();
  const bandColor = BAND_COLORS[band];
  const fontSize = size === 'lg' ? 14 : size === 'sm' ? 10 : 12;

  return (
    <View
      style={[
        styles.container,
        {
          borderColor: bandColor,
          backgroundColor: `${bandColor}22`,
          paddingHorizontal: size === 'sm' ? 6 : 10,
          paddingVertical: size === 'sm' ? 2 : 4,
        },
      ]}
    >
      <Text style={[styles.band, { color: bandColor, fontSize }]}>{band}</Text>
      {showScore && (
        <Text style={[styles.score, { color: theme.colors.textMono, fontSize }]}>
          {score}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 4,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  band: {
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  score: {
    fontFamily: 'monospace',
    fontWeight: '600',
  },
});
