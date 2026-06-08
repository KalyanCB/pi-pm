import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { useAuthStore } from '@pipm/hooks';
import { useUiStore } from '@pipm/hooks';

export function InvestorTopBar() {
  const theme = useTheme();
  const user = useAuthStore((s) => s.user);
  const portfolioId = useAuthStore((s) => s.activePortfolioId);
  const toggleCopilot = useUiStore((s) => s.toggleCopilotPanel);
  const copilotOpen = useUiStore((s) => s.copilotPanelOpen);

  return (
    <View style={[styles.bar, { backgroundColor: theme.colors.backgroundElevated, borderBottomColor: theme.colors.border }]}>
      <Text style={[styles.context, { color: theme.colors.textMuted }]}>
        {user?.displayName ?? 'Investor'}
        {portfolioId ? ` · ${portfolioId.slice(0, 8)}` : ''}
      </Text>
      <Pressable
        onPress={toggleCopilot}
        style={[
          styles.copilotBtn,
          {
            backgroundColor: copilotOpen ? theme.colors.sidebarActive : theme.colors.backgroundPanel,
            borderColor: theme.colors.accent,
          },
        ]}
      >
        <Text style={[styles.copilotText, { color: theme.colors.accent }]}>
          {copilotOpen ? 'Copilot ◂' : 'Copilot ▸'}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  context: {
    fontSize: 12,
    fontFamily: 'monospace',
  },
  copilotBtn: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  copilotText: {
    fontSize: 12,
    fontWeight: '700',
  },
});
