import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useBreakpoint } from '@pipm/theme';

export interface MasterDetailLayoutProps {
  master: React.ReactNode;
  detail: React.ReactNode | null;
}

export function MasterDetailLayout({ master, detail }: MasterDetailLayoutProps) {
  const { isDesktop } = useBreakpoint();

  if (!isDesktop || !detail) {
    return <View style={styles.stack}>{master}</View>;
  }

  return (
    <View style={styles.row}>
      <View style={styles.master}>{master}</View>
      <View style={styles.detail}>{detail}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  stack: {
    gap: 12,
  },
  row: {
    flexDirection: 'row',
    gap: 16,
    alignItems: 'flex-start',
  },
  master: {
    flex: 2,
    minWidth: 280,
  },
  detail: {
    flex: 3,
    minWidth: 0,
  },
});
