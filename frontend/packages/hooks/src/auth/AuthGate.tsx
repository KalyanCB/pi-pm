import React, { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { useRouter, useSegments, usePathname, useRootNavigationState } from 'expo-router';
import { AUTH_BYPASS_ENABLED } from './authBypass';
import { useAuthStore } from '../stores/authStore';

export function AuthGate({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((s) => s.status);
  const router = useRouter();
  const segments = useSegments();
  const pathname = usePathname();
  const rootNavigationState = useRootNavigationState();

  const isLoginRoute = pathname === '/login' || segments[0] === 'login';
  const navigationReady = Boolean(rootNavigationState?.key);
  const showBootOverlay =
    !navigationReady ||
    status === 'bootstrapping' ||
    (!AUTH_BYPASS_ENABLED && status === 'unauthenticated' && !isLoginRoute);

  useEffect(() => {
    if (!navigationReady) return;
    if (status === 'bootstrapping') return;

    if (!AUTH_BYPASS_ENABLED && status === 'unauthenticated' && !isLoginRoute) {
      router.replace('/login');
      return;
    }
    if (status === 'authenticated' && isLoginRoute) {
      router.replace('/');
    }
  }, [status, isLoginRoute, router, navigationReady]);

  return (
    <View style={styles.wrap}>
      {children}
      {showBootOverlay ? (
        <View style={styles.overlay}>
          <ActivityIndicator size="large" color="#3d8bfd" />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0d1117',
  },
});
