import React, { useRef, useState, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { useTheme } from '@pipm/theme';
import { useAskCopilot, useCopilotStore, useUiStore } from '@pipm/hooks';
import { CopilotMessage } from './CopilotMessage';
import { LineagePanel } from './LineagePanel';
import { CopilotQuickQuestions } from './CopilotQuickQuestions';
import { CopilotProgress } from './CopilotProgress';

export function CopilotSidePanel() {
  const theme = useTheme();
  const setOpen = useUiStore((s) => s.setCopilotPanelOpen);
  const messages = useCopilotStore((s) => s.messages);
  const prefill = useCopilotStore((s) => s.prefillQuestion);
  const resetSession = useCopilotStore((s) => s.resetSession);
  const [question, setQuestion] = useState(prefill ?? '');
  const scrollRef = useRef<ScrollView>(null);
  const { mutate, isPending } = useAskCopilot();

  useEffect(() => {
    if (prefill) setQuestion(prefill);
  }, [prefill]);

  const handleAsk = (q?: string) => {
    const text = (q ?? question).trim();
    if (!text || isPending) return;
    setQuestion('');
    mutate(text);
  };

  return (
    <View
      style={[
        styles.panel,
        {
          backgroundColor: theme.colors.backgroundElevated,
          borderLeftColor: theme.colors.border,
        },
      ]}
    >
      <View style={[styles.header, { borderBottomColor: theme.colors.border }]}>
        <Text style={[styles.title, { color: theme.colors.textPrimary }]}>Copilot</Text>
        <View style={styles.headerActions}>
          <Pressable onPress={resetSession}>
            <Text style={[styles.action, { color: theme.colors.textMuted }]}>New</Text>
          </Pressable>
          <Pressable onPress={() => setOpen(false)}>
            <Text style={[styles.action, { color: theme.colors.accent }]}>Close</Text>
          </Pressable>
        </View>
      </View>

      <ScrollView
        ref={scrollRef}
        style={styles.chat}
        contentContainerStyle={styles.chatContent}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.length === 0 && <CopilotQuickQuestions onSelect={handleAsk} />}
        {messages.map((msg) => (
          <View key={msg.id}>
            <CopilotMessage
              role={msg.role}
              content={msg.content}
              intent={msg.intent}
              refused={msg.refused}
              citations={msg.citations}
              uncitedClaims={msg.uncitedClaims}
            />
            {msg.lineage && <LineagePanel lineage={msg.lineage} />}
          </View>
        ))}
        {isPending && <CopilotProgress />}
      </ScrollView>

      <View style={[styles.inputRow, { borderTopColor: theme.colors.border }]}>
        <TextInput
          style={[styles.input, { color: theme.colors.textPrimary }]}
          value={question}
          onChangeText={setQuestion}
          placeholder="Ask about recommendations, risk, committee…"
          placeholderTextColor={theme.colors.textMuted}
          multiline
        />
        <Pressable
          onPress={() => handleAsk()}
          disabled={isPending || !question.trim()}
          style={[styles.send, { backgroundColor: theme.colors.accent, opacity: isPending ? 0.5 : 1 }]}
        >
          <Text style={styles.sendText}>Ask</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    width: 400,
    borderLeftWidth: 1,
    height: '100%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  headerActions: {
    flexDirection: 'row',
    gap: 16,
  },
  action: {
    fontSize: 12,
    fontWeight: '600',
  },
  chat: {
    flex: 1,
  },
  chatContent: {
    padding: 12,
    gap: 6,
  },
  inputRow: {
    borderTopWidth: 1,
    padding: 12,
    gap: 8,
  },
  input: {
    fontSize: 13,
    maxHeight: 80,
    paddingVertical: 8,
  },
  send: {
    borderRadius: 4,
    paddingVertical: 10,
    alignItems: 'center',
  },
  sendText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 13,
  },
});
