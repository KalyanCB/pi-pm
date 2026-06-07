import React from 'react';
import { View, Text, StyleSheet, ScrollView, type ViewStyle } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface InvestorScreenShellProps {
  title: string;
  subtitle?: React.ReactNode;
  headerRight?: React.ReactNode;
  children?: React.ReactNode;
  contentStyle?: ViewStyle;
}

export function InvestorScreenShell({
  title,
  subtitle,
  headerRight,
  children,
  contentStyle,
}: InvestorScreenShellProps) {
  const theme = useTheme();

  return (
    <ScrollView
      style={[styles.scroll, { backgroundColor: theme.colors.background }]}
      contentContainerStyle={[styles.content, contentStyle]}
    >
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={[styles.title, { color: theme.colors.textPrimary }]}>{title}</Text>
          {subtitle &&
            (typeof subtitle === 'string' ? (
              <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>{subtitle}</Text>
            ) : (
              <View style={styles.subtitleBlock}>{subtitle}</View>
            ))}
        </View>
        {headerRight}
      </View>
      {children}
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
    maxWidth: 1440,
    width: '100%',
    alignSelf: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
  },
  headerText: {
    flex: 1,
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
  subtitleBlock: {
    gap: 4,
  },
});
