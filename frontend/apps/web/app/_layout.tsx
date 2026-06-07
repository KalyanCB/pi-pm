import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Slot, usePathname, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ThemeProvider } from '@pipm/theme';
import { AppProviders, AuthGate } from '@pipm/hooks';
import { AppShell } from '@pipm/navigation';

export default function RootLayout() {
  const pathname = usePathname();
  const router = useRouter();
  const isLogin = pathname === '/login';

  const handleNavigate = (href: string) => {
    router.push(href as '/');
  };

  return (
    <ThemeProvider>
      <AppProviders>
        <AuthGate>
          <View style={styles.root}>
            <StatusBar style="light" />
            {isLogin ? (
              <Slot />
            ) : (
              <AppShell activePath={pathname} onNavigate={handleNavigate}>
                <Slot />
              </AppShell>
            )}
          </View>
        </AuthGate>
      </AppProviders>
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    height: '100%',
  },
});
