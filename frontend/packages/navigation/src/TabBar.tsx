import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useTheme } from '@pipm/theme';
import { NAV_ITEMS } from './routes';

export interface TabBarProps {
  activePath: string;
  onNavigate: (href: string) => void;
}

/** Mobile bottom tab bar — uses first 5 primary nav items */
export function TabBar({ activePath, onNavigate }: TabBarProps) {
  const theme = useTheme();
  const tabs = NAV_ITEMS;

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: theme.colors.backgroundElevated,
          borderTopColor: theme.colors.border,
        },
      ]}
    >
      {tabs.map((item) => {
        const isActive =
          activePath === item.href ||
          (item.href !== '/' && activePath.startsWith(item.href));
        return (
          <Pressable
            key={item.key}
            onPress={() => onNavigate(item.href)}
            style={styles.tab}
            accessibilityRole="tab"
            accessibilityState={{ selected: isActive }}
          >
            <Text
              style={[
                styles.icon,
                { color: isActive ? theme.colors.accent : theme.colors.textMuted },
              ]}
            >
              {item.icon}
            </Text>
            <Text
              style={[
                styles.label,
                {
                  color: isActive ? theme.colors.accent : theme.colors.textMuted,
                  fontWeight: isActive ? '600' : '400',
                },
              ]}
            >
              {item.label.split(' ')[0]}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    borderTopWidth: 1,
    paddingBottom: 4,
    paddingTop: 8,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
  },
  icon: {
    fontSize: 16,
  },
  label: {
    fontSize: 10,
  },
});
