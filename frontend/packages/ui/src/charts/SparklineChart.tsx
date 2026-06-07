import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Polyline, Defs, LinearGradient, Stop, Polygon } from 'react-native-svg';
import { useTheme } from '@pipm/theme';

export interface SparklineChartProps {
  data: number[];
  height?: number;
  color?: string;
  fill?: boolean;
  emptyLabel?: string;
}

const MAX_POINTS = 90;

export function SparklineChart({
  data,
  height = 80,
  color,
  fill = true,
  emptyLabel = 'No history available',
}: SparklineChartProps) {
  const theme = useTheme();
  const stroke = color ?? theme.colors.accent;
  const width = 280;

  const { points, fillPoints, label } = useMemo(() => {
    const slice = data.slice(-MAX_POINTS);
    if (slice.length < 2) {
      return { points: '', fillPoints: '', label: emptyLabel };
    }
    const min = Math.min(...slice);
    const max = Math.max(...slice);
    const range = max - min || 1;
    const coords = slice.map((v, i) => {
      const x = (i / (slice.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 8) - 4;
      return `${x},${y}`;
    });
    const last = slice[slice.length - 1]!;
    const first = slice[0]!;
    const summary = `Latest ${last.toFixed(2)}, range ${min.toFixed(2)}–${max.toFixed(2)}`;
    return {
      points: coords.join(' '),
      fillPoints: `0,${height} ${coords.join(' ')} ${width},${height}`,
      label: summary,
    };
  }, [data, height, emptyLabel, width]);

  if (data.length < 2) {
    return (
      <View style={[styles.empty, { height }]}>
        <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>{emptyLabel}</Text>
      </View>
    );
  }

  return (
    <View accessibilityLabel={label}>
      <Svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        {fill && (
          <Defs>
            <LinearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={stroke} stopOpacity="0.25" />
              <Stop offset="1" stopColor={stroke} stopOpacity="0" />
            </LinearGradient>
          </Defs>
        )}
        {fill && <Polygon points={fillPoints} fill="url(#sparkFill)" />}
        <Polyline points={points} fill="none" stroke={stroke} strokeWidth={1.5} />
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  empty: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 11,
  },
});
