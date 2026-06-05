import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useBreakpoint } from '@pipm/theme';
import { Sidebar } from './Sidebar';
import { TabBar } from './TabBar';

export interface AppShellProps {
  children: React.ReactNode;
  activePath: string;
  onNavigate: (href: string) => void;
}

/** Responsive shell — sidebar on desktop, bottom tabs on mobile */
export function AppShell({ children, activePath, onNavigate }: AppShellProps) {
  const { isDesktop } = useBreakpoint();

  if (isDesktop) {
    return (
      <View style={styles.desktopRoot}>
        <Sidebar activePath={activePath} onNavigate={onNavigate} />
        <View style={styles.desktopContent}>{children}</View>
      </View>
    );
  }

  return (
    <View style={styles.mobileRoot}>
      <View style={styles.mobileContent}>{children}</View>
      <TabBar activePath={activePath} onNavigate={onNavigate} />
    </View>
  );
}

const styles = StyleSheet.create({
  desktopRoot: {
    flex: 1,
    flexDirection: 'row',
    height: '100%',
  },
  desktopContent: {
    flex: 1,
    minWidth: 0,
  },
  mobileRoot: {
    flex: 1,
  },
  mobileContent: {
    flex: 1,
  },
});
