import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

const QUESTIONS = [
  'Why recommended?',
  'Why not recommended?',
  'Why exit?',
  'Why is conviction high?',
  'What concerns the committee?',
  'What is portfolio risk?',
  'How is performance trending?',
];

export interface CopilotQuickQuestionsProps {
  onSelect: (question: string) => void;
}

export function CopilotQuickQuestions({ onSelect }: CopilotQuickQuestionsProps) {
  const theme = useTheme();
  return (
    <View style={styles.wrap}>
      <Text style={[styles.label, { color: theme.colors.textMuted }]}>QUICK QUESTIONS</Text>
      <View style={styles.chips}>
        {QUESTIONS.map((q) => (
          <Pressable
            key={q}
            onPress={() => onSelect(q)}
            style={[styles.chip, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel }]}
          >
            <Text style={[styles.chipText, { color: theme.colors.textSecondary }]}>{q}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 8,
    paddingVertical: 8,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  chipText: {
    fontSize: 11,
  },
});
