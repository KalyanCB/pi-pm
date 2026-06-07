import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.wrap,
        { backgroundColor: theme.colors.highConcernBg, borderColor: theme.colors.highConcern },
      ]}
    >
      <Text style={[styles.message, { color: theme.colors.textPrimary }]}>{message}</Text>
      {onRetry && (
        <Pressable onPress={onRetry} style={[styles.btn, { borderColor: theme.colors.accent }]}>
          <Text style={[styles.btnText, { color: theme.colors.accent }]}>Retry</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 16,
    gap: 12,
    alignItems: 'center',
  },
  message: {
    fontSize: 13,
    textAlign: 'center',
  },
  btn: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  btnText: {
    fontSize: 13,
    fontWeight: '600',
  },
});
