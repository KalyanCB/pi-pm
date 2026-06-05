import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import type { CopilotMessageProps } from '@pipm/types';
import { CitationPanel } from './CitationPanel';

export function CopilotMessage({
  role,
  content,
  intent,
  refused = false,
  citations = [],
  uncitedClaims = [],
}: CopilotMessageProps) {
  const theme = useTheme();
  const isUser = role === 'user';

  return (
    <View
      style={[
        styles.wrapper,
        isUser ? styles.userWrapper : styles.assistantWrapper,
      ]}
    >
      <View
        style={[
          styles.bubble,
          {
            backgroundColor: isUser
              ? theme.colors.sidebarActive
              : refused
                ? theme.colors.highConcernBg
                : theme.colors.backgroundPanel,
            borderColor: refused ? theme.colors.highConcern : theme.colors.border,
            borderLeftWidth: refused ? 3 : 1,
          },
        ]}
      >
        {refused && (
          <Text style={[styles.refusedLabel, { color: theme.colors.highConcern }]}>
            REFUSED
          </Text>
        )}
        <Text style={[styles.content, { color: theme.colors.textPrimary }]}>{content}</Text>
        {!isUser && citations.length > 0 && <CitationPanel citations={citations} />}
        {!isUser && uncitedClaims.length > 0 && (
          <Text style={[styles.uncited, { color: theme.colors.warning }]}>
            ⚠ Uncited: {uncitedClaims.join(', ')}
          </Text>
        )}
        {intent && !isUser && (
          <Text style={[styles.intent, { color: theme.colors.textMuted }]}>{intent}</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginVertical: 4,
  },
  userWrapper: {
    alignItems: 'flex-end',
  },
  assistantWrapper: {
    alignItems: 'flex-start',
  },
  bubble: {
    maxWidth: '90%',
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 4,
  },
  refusedLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
    marginBottom: 4,
  },
  content: {
    fontSize: 14,
    lineHeight: 20,
  },
  uncited: {
    fontSize: 11,
    marginTop: 4,
  },
  intent: {
    fontSize: 10,
    fontFamily: 'monospace',
    marginTop: 4,
  },
});
