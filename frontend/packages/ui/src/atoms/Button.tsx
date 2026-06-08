import React from 'react';
import { Pressable, Text, StyleSheet, ActivityIndicator, type ViewStyle } from 'react-native';
import { useTheme } from '@pipm/theme';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost';

export interface ButtonProps {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  disabled = false,
  loading = false,
  style,
}: ButtonProps) {
  const theme = useTheme();
  const isDisabled = disabled || loading;

  const bg =
    variant === 'primary'
      ? theme.colors.accent
      : variant === 'danger'
        ? theme.colors.highConcernBg
        : 'transparent';
  const border =
    variant === 'secondary'
      ? theme.colors.border
      : variant === 'danger'
        ? theme.colors.highConcern
        : variant === 'ghost'
          ? 'transparent'
          : theme.colors.accent;
  const textColor =
    variant === 'primary'
      ? '#fff'
      : variant === 'danger'
        ? theme.colors.highConcern
        : variant === 'secondary'
          ? theme.colors.textPrimary
          : theme.colors.accent;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={[
        styles.btn,
        {
          backgroundColor: bg,
          borderColor: border,
          opacity: isDisabled ? 0.5 : 1,
        },
        style,
      ]}
      accessibilityRole="button"
    >
      {loading ? (
        <ActivityIndicator color={textColor} size="small" />
      ) : (
        <Text style={[styles.label, { color: textColor }]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 10,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
});
