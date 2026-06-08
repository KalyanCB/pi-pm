import React from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface DatePickerProps {
  value: string;
  onChange: (isoDate: string) => void;
  min?: string;
  max?: string;
  label?: string;
}

export function DatePicker({ value, onChange, min, max, label = 'As of' }: DatePickerProps) {
  const theme = useTheme();

  if (Platform.OS === 'web') {
    return (
      <View style={styles.row}>
        <Text style={[styles.label, { color: theme.colors.textMuted }]}>{label}</Text>
        {/* eslint-disable-next-line react/forbid-elements */}
        <input
          type="date"
          value={value}
          min={min}
          max={max}
          onChange={(e) => onChange(e.target.value)}
          style={{
            backgroundColor: theme.colors.backgroundPanel,
            color: theme.colors.textPrimary,
            border: `1px solid ${theme.colors.border}`,
            borderRadius: 4,
            padding: '6px 10px',
            fontSize: 13,
            fontFamily: 'monospace',
          }}
        />
      </View>
    );
  }

  return (
    <View style={styles.row}>
      <Text style={[styles.label, { color: theme.colors.textMuted }]}>{label}</Text>
      <Text style={[styles.value, { color: theme.colors.textPrimary, borderColor: theme.colors.border }]}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  label: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  value: {
    fontSize: 13,
    fontFamily: 'monospace',
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
});
