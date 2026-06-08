import React from 'react';
import { View, Text, StyleSheet, Pressable, type ViewStyle } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface MetricCardProps {
  label: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  highlight?: boolean;
  alert?: boolean;
  onPress?: () => void;
  style?: ViewStyle;
}

export function MetricCard({
  label,
  children,
  footer,
  highlight = false,
  alert = false,
  onPress,
  style,
}: MetricCardProps) {
  const theme = useTheme();
  const borderColor = alert
    ? theme.colors.highConcern
    : highlight
      ? theme.colors.accent
      : theme.colors.border;

  const content = (
    <View
      style={[
        styles.card,
        {
          backgroundColor: alert ? theme.colors.highConcernBg : theme.colors.backgroundPanel,
          borderColor,
          borderLeftWidth: alert ? 3 : 1,
        },
        style,
      ]}
    >
      <Text style={[styles.label, { color: theme.colors.textMuted }]}>{label}</Text>
      <View style={styles.body}>{children}</View>
      {footer && <View style={styles.footer}>{footer}</View>}
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
    gap: 6,
    flex: 1,
    minWidth: 140,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  body: {
    gap: 4,
  },
  footer: {
    marginTop: 4,
  },
});
