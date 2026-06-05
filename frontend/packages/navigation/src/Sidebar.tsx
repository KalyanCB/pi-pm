import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { NAV_ITEMS, SECONDARY_NAV } from './routes';

export interface SidebarProps {
  activePath: string;
  onNavigate: (href: string) => void;
  collapsed?: boolean;
}

export function Sidebar({ activePath, onNavigate, collapsed = false }: SidebarProps) {
  const theme = useTheme();

  const renderItem = (item: (typeof NAV_ITEMS)[number]) => {
    const isActive =
      activePath === item.href ||
      (item.href !== '/' && activePath.startsWith(item.href));
    return (
      <Pressable
        key={item.key}
        onPress={() => onNavigate(item.href)}
        style={[
          styles.item,
          {
            backgroundColor: isActive ? theme.colors.sidebarActive : 'transparent',
            borderLeftColor: isActive ? theme.colors.accent : 'transparent',
          },
        ]}
        accessibilityRole="button"
        accessibilityLabel={item.label}
      >
        <Text style={[styles.icon, { color: theme.colors.accent }]}>{item.icon}</Text>
        {!collapsed && (
          <Text
            style={[
              styles.label,
              {
                color: isActive ? theme.colors.textPrimary : theme.colors.textSecondary,
                fontWeight: isActive ? '600' : '400',
              },
            ]}
          >
            {item.label}
          </Text>
        )}
      </Pressable>
    );
  };

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.sidebar,
          borderRightColor: theme.colors.border,
          width: collapsed ? 56 : 240,
        },
      ]}
    >
      <View style={styles.brand}>
        <Text style={[styles.brandText, { color: theme.colors.textPrimary }]}>
          {collapsed ? 'PM' : 'Pi-PM'}
        </Text>
        {!collapsed && (
          <Text style={[styles.brandSub, { color: theme.colors.textMuted }]}>
            Portfolio Console
          </Text>
        )}
      </View>
      <View style={styles.nav}>{NAV_ITEMS.map(renderItem)}</View>
      <View style={[styles.footer, { borderTopColor: theme.colors.border }]}>
        {SECONDARY_NAV.map(renderItem)}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRightWidth: 1,
    height: '100%',
  },
  brand: {
    paddingHorizontal: 16,
    paddingVertical: 20,
  },
  brandText: {
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: 1,
  },
  brandSub: {
    fontSize: 11,
    marginTop: 2,
    letterSpacing: 0.5,
  },
  nav: {
    flex: 1,
    paddingTop: 8,
  },
  footer: {
    borderTopWidth: 1,
    paddingVertical: 8,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderLeftWidth: 3,
    gap: 12,
  },
  icon: {
    fontSize: 14,
    width: 20,
    textAlign: 'center',
  },
  label: {
    fontSize: 14,
  },
});
