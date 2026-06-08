import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { useTheme } from '@pipm/theme';
import { useAuth } from '@pipm/hooks';

export function LoginScreen() {
  const theme = useTheme();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await login({ email: email.trim(), password });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.root, { backgroundColor: theme.colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={[styles.card, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border }]}>
        <Text style={[styles.brand, { color: theme.colors.accent }]}>PI-PM</Text>
        <Text style={[styles.subtitle, { color: theme.colors.textMuted }]}>Investor Portal</Text>

        <Text style={[styles.label, { color: theme.colors.textMuted }]}>Email</Text>
        <TextInput
          style={[styles.input, { color: theme.colors.textPrimary, borderColor: theme.colors.border, backgroundColor: theme.colors.background }]}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          autoComplete="email"
          placeholder="you@example.com"
          placeholderTextColor={theme.colors.textMuted}
        />

        <Text style={[styles.label, { color: theme.colors.textMuted }]}>Password</Text>
        <TextInput
          style={[styles.input, { color: theme.colors.textPrimary, borderColor: theme.colors.border, backgroundColor: theme.colors.background }]}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="password"
          placeholder="••••••••"
          placeholderTextColor={theme.colors.textMuted}
        />

        {error && <Text style={[styles.error, { color: theme.colors.highConcern }]}>{error}</Text>}

        <Pressable
          onPress={() => void handleSubmit()}
          disabled={loading || !email || !password}
          style={[
            styles.button,
            { backgroundColor: theme.colors.accent, opacity: loading || !email || !password ? 0.6 : 1 },
          ]}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Sign in</Text>
          )}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderRadius: 8,
    padding: 24,
    gap: 8,
  },
  brand: {
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: 2,
  },
  subtitle: {
    fontSize: 13,
    marginBottom: 16,
  },
  label: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 8,
  },
  input: {
    borderWidth: 1,
    borderRadius: 4,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  error: {
    fontSize: 13,
    marginTop: 8,
  },
  button: {
    marginTop: 16,
    borderRadius: 4,
    paddingVertical: 12,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
  },
});
