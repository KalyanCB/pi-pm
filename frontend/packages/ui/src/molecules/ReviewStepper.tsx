import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

const STEPS = ['Engine', 'Committee', 'Your Decision'] as const;

export interface ReviewStepperProps {
  engineReviewed?: boolean;
  committeeReviewed?: boolean;
}

export function ReviewStepper({ engineReviewed = true, committeeReviewed = false }: ReviewStepperProps) {
  const theme = useTheme();
  const done = [engineReviewed, committeeReviewed, false];

  return (
    <View style={styles.row}>
      {STEPS.map((step, i) => (
        <View key={step} style={styles.step}>
          <View
            style={[
              styles.dot,
              {
                backgroundColor: done[i] ? theme.colors.positive : theme.colors.border,
                borderColor: done[i] ? theme.colors.positive : theme.colors.textMuted,
              },
            ]}
          />
          <Text style={[styles.label, { color: done[i] ? theme.colors.textPrimary : theme.colors.textMuted }]}>
            {step}
          </Text>
          {i < STEPS.length - 1 && (
            <View style={[styles.line, { backgroundColor: theme.colors.border }]} />
          )}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    flexWrap: 'wrap',
  },
  step: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    borderWidth: 1,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  line: {
    width: 16,
    height: 1,
    marginHorizontal: 4,
  },
});
