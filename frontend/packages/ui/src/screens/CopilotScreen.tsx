import React, { useRef, useState, useEffect } from 'react';
import {
  View,
  TextInput,
  Pressable,
  Text,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useTheme } from '@pipm/theme';
import { useAskCopilot, useCopilotStore } from '@pipm/hooks';
import { InvestorScreenShell } from '../layout/InvestorScreenShell';
import { CopilotMessage } from '../molecules/CopilotMessage';
import { LineagePanel } from '../molecules/LineagePanel';
import { CopilotQuickQuestions } from '../molecules/CopilotQuickQuestions';
import { CitationPanel } from '../molecules/CitationPanel';

export function CopilotScreen() {
  const theme = useTheme();
  const messages = useCopilotStore((s) => s.messages);
  const prefill = useCopilotStore((s) => s.prefillQuestion);
  const resetSession = useCopilotStore((s) => s.resetSession);
  const [question, setQuestion] = useState(prefill ?? '');
  const scrollRef = useRef<ScrollView>(null);
  const { mutate, isPending, error } = useAskCopilot();

  useEffect(() => {
    if (prefill) setQuestion(prefill);
  }, [prefill]);

  const handleAsk = (q?: string) => {
    const text = (q ?? question).trim();
    if (!text || isPending) return;
    setQuestion('');
    mutate(text, {
      onSettled: () => scrollRef.current?.scrollToEnd({ animated: true }),
    });
  };

  return (
    <InvestorScreenShell title="Copilot" subtitle="Grounded decision support · Citations · Lineage">
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={80}
      >
        <ScrollView
          ref={scrollRef}
          style={[styles.chat, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
          contentContainerStyle={styles.chatContent}
        >
          {messages.length === 0 && <CopilotQuickQuestions onSelect={handleAsk} />}
          {messages.map((msg) => (
            <View key={msg.id} style={styles.msgBlock}>
              <CopilotMessage
                role={msg.role}
                content={msg.content}
                intent={msg.intent}
                refused={msg.refused}
                citations={msg.citations}
                uncitedClaims={msg.uncitedClaims}
              />
              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <View style={styles.evidence}>
                  <Text style={[styles.evidenceLabel, { color: theme.colors.textMuted }]}>SOURCES</Text>
                  <CitationPanel citations={msg.citations} />
                </View>
              )}
              {msg.lineage && <LineagePanel lineage={msg.lineage} />}
            </View>
          ))}
          {isPending && <ActivityIndicator color={theme.colors.accent} style={styles.pending} />}
          {error && (
            <Text style={[styles.error, { color: theme.colors.highConcern }]}>
              {error instanceof Error ? error.message : 'Request failed'}
            </Text>
          )}
        </ScrollView>

        <View style={[styles.inputRow, { borderColor: theme.colors.border, backgroundColor: theme.colors.backgroundElevated }]}>
          <TextInput
            style={[styles.input, { color: theme.colors.textPrimary }]}
            value={question}
            onChangeText={setQuestion}
            placeholder="Ask a question…"
            placeholderTextColor={theme.colors.textMuted}
            multiline
          />
          <Pressable
            onPress={() => handleAsk()}
            disabled={isPending || !question.trim()}
            style={[styles.sendBtn, { backgroundColor: theme.colors.accent, opacity: isPending ? 0.5 : 1 }]}
          >
            <Text style={styles.sendText}>Ask</Text>
          </Pressable>
          <Pressable onPress={resetSession} style={styles.clearBtn}>
            <Text style={[styles.clearText, { color: theme.colors.textMuted }]}>New</Text>
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </InvestorScreenShell>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, minHeight: 400 },
  chat: { borderWidth: 1, borderRadius: 6, flex: 1, maxHeight: 560 },
  chatContent: { padding: 12, gap: 8 },
  msgBlock: { gap: 4 },
  evidence: { marginLeft: 8, gap: 4 },
  evidenceLabel: { fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  pending: { marginTop: 8 },
  error: { fontSize: 12 },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    borderTopWidth: 1,
    padding: 12,
    marginTop: 12,
    borderRadius: 6,
  },
  input: { flex: 1, fontSize: 14, maxHeight: 100, paddingVertical: 8 },
  sendBtn: { borderRadius: 4, paddingHorizontal: 16, paddingVertical: 10 },
  sendText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  clearBtn: { padding: 10 },
  clearText: { fontSize: 12 },
});
