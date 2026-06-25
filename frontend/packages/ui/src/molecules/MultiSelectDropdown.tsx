import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet, ScrollView } from 'react-native';
import { useTheme } from '@pipm/theme';

export interface MultiSelectDropdownProps {
  /** Short field label shown inside the trigger (e.g. "Sector"). */
  label: string;
  options: string[];
  /** Currently selected values. Empty array = "All". */
  selected: string[];
  onChange: (next: string[]) => void;
}

/**
 * Compact multi-select dropdown. Collapsed it is a single pill (label + summary),
 * so it takes far less space than a row of chips. Open it overlays a checklist.
 */
export function MultiSelectDropdown({ label, options, selected, onChange }: MultiSelectDropdownProps) {
  const theme = useTheme();
  const [open, setOpen] = useState(false);

  const toggle = (opt: string) =>
    onChange(selected.includes(opt) ? selected.filter((s) => s !== opt) : [...selected, opt]);

  const summary =
    selected.length === 0 ? 'All' : selected.length === 1 ? selected[0] : `${selected.length} selected`;

  return (
    <View style={[styles.wrap, open && styles.wrapOpen]}>
      <Pressable
        onPress={() => setOpen((o) => !o)}
        style={[styles.trigger, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border }]}
      >
        <Text style={[styles.label, { color: theme.colors.textMuted }]}>{label}</Text>
        <Text
          style={[styles.value, { color: selected.length ? theme.colors.accent : theme.colors.textSecondary }]}
          numberOfLines={1}
        >
          {summary}
        </Text>
        <Text style={[styles.caret, { color: theme.colors.textMuted }]}>{open ? '▲' : '▼'}</Text>
      </Pressable>

      {open && (
        <View style={[styles.menu, { backgroundColor: theme.colors.backgroundPanel, borderColor: theme.colors.border }]}>
          <ScrollView style={styles.menuScroll} keyboardShouldPersistTaps="handled">
            <Pressable style={styles.item} onPress={() => onChange([])}>
              <Text style={[styles.box, { color: selected.length === 0 ? theme.colors.accent : theme.colors.textMuted }]}>
                {selected.length === 0 ? '◉' : '○'}
              </Text>
              <Text style={[styles.itemText, { color: theme.colors.textPrimary }]}>All</Text>
            </Pressable>
            {options.map((opt) => {
              const on = selected.includes(opt);
              return (
                <Pressable key={opt} style={styles.item} onPress={() => toggle(opt)}>
                  <Text style={[styles.box, { color: on ? theme.colors.accent : theme.colors.textMuted }]}>
                    {on ? '☑' : '☐'}
                  </Text>
                  <Text style={[styles.itemText, { color: theme.colors.textPrimary }]}>{opt}</Text>
                </Pressable>
              );
            })}
          </ScrollView>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'relative' },
  wrapOpen: { zIndex: 1000 },
  trigger: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 7,
    minWidth: 170,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  value: { flex: 1, fontSize: 12, fontWeight: '600' },
  caret: { fontSize: 9 },
  menu: {
    position: 'absolute',
    top: 38,
    left: 0,
    minWidth: 200,
    borderWidth: 1,
    borderRadius: 6,
    paddingVertical: 4,
    zIndex: 1000,
    // subtle elevation on web
    ...(typeof window !== 'undefined' ? { boxShadow: '0 6px 18px rgba(0,0,0,0.35)' } : {}),
  },
  menuScroll: { maxHeight: 220 },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  box: { fontSize: 14, width: 16 },
  itemText: { fontSize: 12, fontWeight: '500' },
});
