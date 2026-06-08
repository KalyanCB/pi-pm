import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useBreakpoint } from '@pipm/theme';
import { useUiStore } from '@pipm/hooks';
import { CopilotSidePanel } from '@pipm/ui';
import { Sidebar } from './Sidebar';
import { TabBar } from './TabBar';
import { InvestorTopBar } from './InvestorTopBar';

export interface AppShellProps {
  children: React.ReactNode;
  activePath: string;
  onNavigate: (href: string) => void;
}

/** Responsive shell — sidebar + copilot panel on desktop, bottom tabs on mobile */
export function AppShell({ children, activePath, onNavigate }: AppShellProps) {
  const { isDesktop } = useBreakpoint();
  const copilotOpen = useUiStore((s) => s.copilotPanelOpen);

  if (isDesktop) {
    return (
      <View style={styles.desktopRoot}>
        <Sidebar activePath={activePath} onNavigate={onNavigate} />
        <View style={styles.desktopMain}>
          <InvestorTopBar />
          <View style={styles.desktopBody}>
            <View style={styles.desktopContent}>{children}</View>
            {copilotOpen && <CopilotSidePanel />}
          </View>
        </View>
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
  desktopMain: {
    flex: 1,
    minWidth: 0,
  },
  desktopBody: {
    flex: 1,
    flexDirection: 'row',
    minHeight: 0,
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
