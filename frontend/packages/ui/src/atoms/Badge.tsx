import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

export interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
}

const variantColors: Record<BadgeVariant, { bg: string; text: string }> = {
  default: { bg: '#1e2a3a', text: '#8b9cb3' },
  success: { bg: '#1a3d2e', text: '#3dba7a' },
  warning: { bg: '#3d3010', text: '#d4a017' },
  danger: { bg: '#3d1a1a', text: '#e05252' },
  info: { bg: '#1a2d3d', text: '#5b9bd5' },
};

export function Badge({ label, variant = 'default', size = 'sm' }: BadgeProps) {
  const theme = useTheme();
  const colors = variantColors[variant];

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: colors.bg,
          borderColor: theme.colors.borderSubtle,
          paddingHorizontal: size === 'sm' ? 6 : 10,
          paddingVertical: size === 'sm' ? 2 : 4,
        },
      ]}
    >
      <Text
        style={[
          styles.text,
          { color: colors.text, fontSize: size === 'sm' ? 10 : 12 },
        ]}
      >
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: 4,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  text: {
    fontWeight: '600',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
});
