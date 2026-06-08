import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

export function LoadingState({ message = 'Loading…' }: { message?: string }) {
  const theme = useTheme();
  return (
    <View style={styles.wrap}>
      <ActivityIndicator size="small" color={theme.colors.accent} />
      <Text style={[styles.text, { color: theme.colors.textMuted }]}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    padding: 24,
    alignItems: 'center',
    gap: 12,
  },
  text: {
    fontSize: 13,
  },
});
