import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';

/**
 * Staged progress shown while a Copilot answer is being generated.
 *
 * The /ask call is a single request, so these stages are time-paced rather than
 * driven by real backend events — but they mirror the actual pipeline
 * (classify intent → retrieve grounded data → generate answer) so the wait
 * feels meaningful instead of a bare spinner.
 */
const STAGES = [
  'Understanding your question…',
  'Gathering data from the corpus…',
  'Reviewing rankings, committee & exits…',
  'Framing the answer…',
];

export interface CopilotProgressProps {
  /** ms per stage before advancing (holds on the last stage). */
  stageMs?: number;
  style?: object;
}

export function CopilotProgress({ stageMs = 4000, style }: CopilotProgressProps) {
  const theme = useTheme();
  const [stage, setStage] = useState(0);

  useEffect(() => {
    setStage(0);
    const id = setInterval(
      () => setStage((s) => (s < STAGES.length - 1 ? s + 1 : s)),
      stageMs,
    );
    return () => clearInterval(id);
  }, [stageMs]);

  return (
    <View
      style={[
        styles.row,
        { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundPanel },
        style,
      ]}
      accessibilityRole="progressbar"
      accessibilityLabel={STAGES[stage]}
    >
      <ActivityIndicator color={theme.colors.accent} />
      <Text style={[styles.label, { color: theme.colors.textSecondary }]}>{STAGES[stage]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  label: {
    fontSize: 13,
    fontWeight: '500',
  },
});
