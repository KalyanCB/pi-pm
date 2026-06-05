import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface HighConcernBannerProps {
  committees: string[];
  displayNames?: Record<string, string>;
  onPress?: () => void;
  compact?: boolean;
}

export function HighConcernBanner({
  committees,
  displayNames = {},
  onPress,
  compact = false,
}: HighConcernBannerProps) {
  const theme = useTheme();
  const labels = committees.map((c) => displayNames[c] ?? c).join(', ');

  const content = (
    <View
      style={[
        styles.banner,
        {
          backgroundColor: theme.colors.highConcernBg,
          borderColor: theme.colors.highConcern,
        },
      ]}
    >
      <Text style={[styles.icon, { color: theme.colors.highConcern }]}>⚠</Text>
      <View style={styles.textBlock}>
        <Text style={[styles.title, { color: theme.colors.highConcern }]}>
          HIGH CONCERN
        </Text>
        {!compact && labels.length > 0 && (
          <Text style={[styles.subtitle, { color: theme.colors.textSecondary }]}>
            {labels}
          </Text>
        )}
      </View>
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
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 8,
    borderRadius: 4,
    borderWidth: 1,
  },
  icon: {
    fontSize: 14,
    fontWeight: '700',
  },
  textBlock: {
    flex: 1,
  },
  title: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 11,
    marginTop: 2,
  },
});
