import React, { useState } from 'react';
import { View, Text, TextInput, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { Button } from '../atoms/Button';

export interface ApprovalActionBarProps {
  action: 'BUY' | 'WATCH' | 'EXIT_APPROVED';
  onApprove: () => void;
  onReject: (note?: string) => void;
  onAskCopilot?: () => void;
  loading?: boolean;
}

export function ApprovalActionBar({
  action,
  onApprove,
  onReject,
  onAskCopilot,
  loading = false,
}: ApprovalActionBarProps) {
  const theme = useTheme();
  const [showReject, setShowReject] = useState(false);
  const [note, setNote] = useState('');

  const approveLabel = action === 'EXIT_APPROVED' ? 'Confirm Exit' : 'Approve';

  return (
    <View style={[styles.bar, { backgroundColor: theme.colors.backgroundElevated, borderColor: theme.colors.border }]}>
      <View style={styles.actions}>
        <Button label={approveLabel} onPress={onApprove} loading={loading} variant="primary" style={styles.btn} />
        <Button
          label="Reject"
          onPress={() => (showReject ? onReject(note || undefined) : setShowReject(true))}
          loading={loading}
          variant="danger"
          style={styles.btn}
        />
        {onAskCopilot && (
          <Button label="Ask Copilot" onPress={onAskCopilot} variant="ghost" style={styles.btn} />
        )}
      </View>
      {showReject && (
        <TextInput
          style={[styles.note, { color: theme.colors.textPrimary, borderColor: theme.colors.border }]}
          placeholder="Rejection note (optional)"
          placeholderTextColor={theme.colors.textMuted}
          value={note}
          onChangeText={setNote}
        />
      )}
      <Text style={[styles.hint, { color: theme.colors.textMuted }]}>
        Review committee advisory before approving
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 12,
    gap: 10,
  },
  actions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  btn: {
    flex: 1,
    minWidth: 120,
  },
  note: {
    borderWidth: 1,
    borderRadius: 4,
    padding: 10,
    fontSize: 13,
  },
  hint: {
    fontSize: 10,
    textAlign: 'center',
  },
});
