import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { useAuth, useAuthStore } from '@pipm/hooks';
import { ScreenShell } from '../feedback/ScreenShell';

export function SettingsScreen() {
  const theme = useTheme();
  const { logout } = useAuth();
  const user = useAuthStore((s) => s.user);
  const portfolios = useAuthStore((s) => s.portfolios);
  const activePortfolioId = useAuthStore((s) => s.activePortfolioId);
  const setActivePortfolio = useAuthStore((s) => s.setActivePortfolio);

  return (
    <ScreenShell title="Settings" subtitle="Account · Portfolio · Session">
      {user && (
        <View style={[styles.card, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border }]}>
          <Text style={[styles.label, { color: theme.colors.textMuted }]}>SIGNED IN AS</Text>
          <Text style={[styles.value, { color: theme.colors.textPrimary }]}>{user.displayName}</Text>
          <Text style={[styles.email, { color: theme.colors.textSecondary }]}>{user.email}</Text>
        </View>
      )}

      {portfolios.length > 0 && (
        <View style={styles.section}>
          <Text style={[styles.label, { color: theme.colors.textMuted }]}>PORTFOLIO</Text>
          {portfolios.map((p) => (
            <Pressable
              key={p.portfolio_id}
              onPress={() => setActivePortfolio(p.portfolio_id)}
              style={[
                styles.portfolioRow,
                {
                  backgroundColor:
                    activePortfolioId === p.portfolio_id
                      ? theme.colors.sidebarActive
                      : theme.colors.backgroundElevated,
                  borderColor: theme.colors.border,
                },
              ]}
            >
              <Text style={[styles.portfolioName, { color: theme.colors.textPrimary }]}>
                {p.name ?? p.portfolio_id.slice(0, 8)}
              </Text>
              <Text style={[styles.portfolioRole, { color: theme.colors.textMuted }]}>{p.role}</Text>
            </Pressable>
          ))}
        </View>
      )}

      <Text style={[styles.apiUrl, { color: theme.colors.textMuted }]}>
        API: {process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1'}
      </Text>

      <Pressable
        onPress={() => void logout()}
        style={[styles.logoutBtn, { borderColor: theme.colors.highConcern }]}
      >
        <Text style={[styles.logoutText, { color: theme.colors.highConcern }]}>Sign out</Text>
      </Pressable>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 6,
    padding: 16,
    gap: 4,
  },
  label: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
  },
  value: {
    fontSize: 16,
    fontWeight: '700',
  },
  email: {
    fontSize: 13,
  },
  section: {
    gap: 8,
  },
  portfolioRow: {
    borderWidth: 1,
    borderRadius: 4,
    padding: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  portfolioName: {
    fontSize: 14,
    fontWeight: '600',
  },
  portfolioRole: {
    fontSize: 11,
    textTransform: 'uppercase',
  },
  apiUrl: {
    fontSize: 11,
    fontFamily: 'monospace',
  },
  logoutBtn: {
    borderWidth: 1,
    borderRadius: 4,
    padding: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  logoutText: {
    fontSize: 14,
    fontWeight: '600',
  },
});
