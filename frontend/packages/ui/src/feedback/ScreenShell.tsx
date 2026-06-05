import React from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface ScreenShellProps {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}

/** Empty screen placeholder — no business logic */
export function ScreenShell({ title, subtitle, children }: ScreenShellProps) {
  const theme = useTheme();

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={styles.content}
    >
      <View style={styles.header}>
        <Text style={[styles.title, { color: theme.colors.textPrimary }]}>{title}</Text>
        {subtitle && (
          <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>{subtitle}</Text>
        )}
      </View>
      {children ?? (
        <View
          style={[
            styles.placeholder,
            {
              backgroundColor: theme.colors.backgroundPanel,
              borderColor: theme.colors.border,
            },
          ]}
        >
          <Text style={[styles.placeholderText, { color: theme.colors.textMuted }]}>
            Content coming in Phase 2
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
  },
  content: {
    padding: 20,
    gap: 16,
  },
  header: {
    gap: 4,
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 13,
  },
  placeholder: {
    borderWidth: 1,
    borderRadius: 6,
    borderStyle: 'dashed',
    padding: 40,
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 13,
  },
});
