import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { CitationPanelProps } from '@pipm/types';

export function CitationPanel({ citations, onPress }: CitationPanelProps) {
  const theme = useTheme();

  if (citations.length === 0) return null;

  return (
    <View style={styles.container}>
      {citations.map((citation, index) => (
        <Pressable
          key={`${citation.ref}-${index}`}
          onPress={() => onPress?.(citation)}
          style={[
            styles.chip,
            {
              backgroundColor: theme.colors.backgroundPanel,
              borderColor: theme.colors.border,
            },
          ]}
          accessibilityRole="link"
        >
          <Text style={[styles.ref, { color: theme.colors.accent }]}>📎</Text>
          <View style={styles.text}>
            <Text style={[styles.table, { color: theme.colors.textSecondary }]}>
              {citation.source_table ?? 'source'}
            </Text>
            {citation.source_value && (
              <Text
                style={[styles.value, { color: theme.colors.textPrimary }]}
                numberOfLines={1}
              >
                {citation.source_field}: {citation.source_value}
              </Text>
            )}
          </View>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 6,
    marginTop: 8,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderRadius: 4,
    padding: 8,
  },
  ref: {
    fontSize: 12,
  },
  text: {
    flex: 1,
    gap: 2,
  },
  table: {
    fontSize: 10,
    fontFamily: 'monospace',
    textTransform: 'uppercase',
  },
  value: {
    fontSize: 11,
  },
});
