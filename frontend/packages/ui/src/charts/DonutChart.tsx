import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { G, Path, Circle } from 'react-native-svg';
import { useTheme } from '@pipm/theme';

export interface DonutSegment {
  label: string;
  value: number;
  color?: string;
}

export interface DonutChartProps {
  segments: DonutSegment[];
  size?: number;
  emptyLabel?: string;
  /** Max number of legend rows to show (default 4). */
  maxLegend?: number;
}

const PALETTE = ['#3d8fd1', '#3dba7a', '#d4a017', '#5b9bd5', '#e07b39', '#8b9cb3'];

function arcPath(cx: number, cy: number, r: number, start: number, end: number): string {
  const x1 = cx + r * Math.cos(start);
  const y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(end);
  const y2 = cy + r * Math.sin(end);
  const large = end - start > Math.PI ? 1 : 0;
  return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
}

export function DonutChart({
  segments,
  size = 160,
  emptyLabel = 'No allocation data',
  maxLegend = 4,
}: DonutChartProps) {
  const theme = useTheme();
  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 4;
  const inner = r * 0.55;

  const { paths, total, topLabels } = useMemo(() => {
    const filtered = segments.filter((s) => s.value > 0);
    const sum = filtered.reduce((a, s) => a + s.value, 0);
    if (sum === 0) return { paths: [], total: 0, topLabels: [] };

    let angle = -Math.PI / 2;
    const paths = filtered.map((seg, i) => {
      const slice = (seg.value / sum) * Math.PI * 2;
      const start = angle;
      const end = angle + slice;
      angle = end;
      return {
        d: arcPath(cx, cy, r, start, end),
        color: seg.color ?? PALETTE[i % PALETTE.length]!,
        label: seg.label,
        pct: (seg.value / sum) * 100,
      };
    });
    return {
      paths,
      total: sum,
      topLabels: paths.slice(0, maxLegend),
    };
  }, [segments, cx, cy, r, maxLegend]);

  if (paths.length === 0) {
    return (
      <View style={[styles.empty, { width: size, height: size }]}>
        <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>{emptyLabel}</Text>
      </View>
    );
  }

  return (
    <View style={styles.wrap}>
      <Svg width={size} height={size}>
        <G>
          {paths.map((p, i) => (
            <Path key={i} d={p.d} fill={p.color} />
          ))}
          <Circle cx={cx} cy={cy} r={inner} fill={theme.colors.backgroundPanel} />
        </G>
      </Svg>
      <View style={styles.legend}>
        {topLabels.map((p) => (
          <View key={p.label} style={styles.legendRow}>
            <View style={[styles.dot, { backgroundColor: p.color }]} />
            <Text style={[styles.legendLabel, { color: theme.colors.textSecondary }]} numberOfLines={1}>
              {p.label}
            </Text>
            <Text style={[styles.legendPct, { color: theme.colors.textMono }]}>
              {p.pct.toFixed(1)}%
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flexWrap: 'wrap',
  },
  empty: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 11,
    textAlign: 'center',
  },
  legend: {
    flex: 1,
    minWidth: 120,
    gap: 4,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendLabel: {
    flex: 1,
    fontSize: 11,
  },
  legendPct: {
    fontSize: 11,
    fontFamily: 'monospace',
  },
});
