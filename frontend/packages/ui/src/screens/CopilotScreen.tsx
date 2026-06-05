import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { ScreenShell } from '../feedback/ScreenShell';
import { CopilotMessage } from '../molecules/CopilotMessage';

/** Shell with sample static messages — no API calls */
export function CopilotScreen() {
  const theme = useTheme();

  return (
    <ScreenShell title="Copilot" subtitle="Grounded Q&A over Pi-PM data">
      <View style={[styles.chat, { backgroundColor: theme.colors.backgroundPanel }]}>
        <CopilotMessage role="user" content="Why is INFY a BUY today?" />
        <CopilotMessage
          role="assistant"
          content="Copilot responses will appear here with citations once connected to the API."
          intent="why_recommended"
          citations={[]}
        />
      </View>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  chat: {
    borderRadius: 6,
    padding: 12,
    gap: 8,
  },
});
