import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Polyline, Defs, LinearGradient, Stop, Polygon, Line, Text as SvgText } from 'react-native-svg';
import { useTheme } from '@pipm/theme';

export interface SparklineChartProps {
  data: number[];
  dates?: string[];        // ISO date strings aligned with data
  height?: number;
  color?: string;
  fill?: boolean;
  emptyLabel?: string;
  showScale?: boolean;     // show Y-axis labels + gridlines
  formatValue?: (v: number) => string;
}

const MAX_POINTS = 90;
const Y_LABEL_W = 52;   // reserved left-margin for Y labels
const X_LABEL_H = 16;   // reserved bottom margin for X labels

function fmtLakh(v: number): string {
  if (Math.abs(v) >= 10_00_000) return `₹${(v / 10_00_000).toFixed(1)}L`;
  if (Math.abs(v) >= 1000) return `₹${(v / 1000).toFixed(0)}K`;
  return `₹${v.toFixed(0)}`;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });
}

export function SparklineChart({
  data,
  dates,
  height = 120,
  color,
  fill = true,
  emptyLabel = 'No history available',
  showScale = false,
  formatValue,
}: SparklineChartProps) {
  const theme = useTheme();
  const stroke = color ?? theme.colors.accent;
  const svgW = 280;
  const plotW = showScale ? svgW - Y_LABEL_W : svgW;
  const plotH = showScale ? height - X_LABEL_H : height;
  const offsetX = showScale ? Y_LABEL_W : 0;

  const fmt = formatValue ?? fmtLakh;

  const { points, fillPoints, min, max, yTicks, xTicks, label } = useMemo(() => {
    // Downsample evenly across the FULL series (not just the last MAX_POINTS) so a
    // long history shows its complete arc — e.g. a NAV trend that starts at ₹10L —
    // instead of being truncated to only the most recent window.
    const sample = <T,>(arr: T[]): T[] =>
      arr.length <= MAX_POINTS
        ? arr
        : Array.from(
            { length: MAX_POINTS },
            (_, i) => arr[Math.round((i * (arr.length - 1)) / (MAX_POINTS - 1))]!,
          );
    const slice = sample(data);
    const dateSlice = dates ? sample(dates) : [];

    if (slice.length < 2) {
      return { points: '', fillPoints: '', min: 0, max: 0, yTicks: [], xTicks: [], label: emptyLabel };
    }

    const minV = Math.min(...slice);
    const maxV = Math.max(...slice);
    const range = maxV - minV || 1;

    const toX = (i: number) => offsetX + (i / (slice.length - 1)) * plotW;
    const toY = (v: number) => plotH - ((v - minV) / range) * (plotH - 8) - 4;

    const coords = slice.map((v, i) => `${toX(i)},${toY(v)}`);
    const last = slice[slice.length - 1]!;
    const summary = `Latest ${last.toFixed(2)}, range ${minV.toFixed(2)}–${maxV.toFixed(2)}`;

    // Y ticks: min, mid, max
    const mid = (minV + maxV) / 2;
    const yTicks = [
      { v: maxV, y: toY(maxV) },
      { v: mid,  y: toY(mid) },
      { v: minV, y: toY(minV) },
    ];

    // X ticks: ~3 evenly spaced date labels
    const xTicks: { label: string; x: number }[] = [];
    if (dateSlice.length >= 2) {
      const idxs = [0, Math.floor(slice.length / 2), slice.length - 1];
      for (const i of idxs) {
        if (dateSlice[i]) xTicks.push({ label: fmtDate(dateSlice[i]!), x: toX(i) });
      }
    }

    return {
      points: coords.join(' '),
      fillPoints: `${offsetX},${plotH} ${coords.join(' ')} ${offsetX + plotW},${plotH}`,
      min: minV, max: maxV,
      yTicks,
      xTicks,
      label: summary,
    };
  }, [data, dates, height, emptyLabel, plotW, plotH, offsetX, fmt]);

  if (data.length < 2) {
    return (
      <View style={[styles.empty, { height }]}>
        <Text style={[styles.emptyText, { color: theme.colors.textMuted }]}>{emptyLabel}</Text>
      </View>
    );
  }

  const totalH = showScale ? height : height;

  return (
    <View accessibilityLabel={label}>
      <Svg width="100%" height={totalH} viewBox={`0 0 ${svgW} ${totalH}`}>
        {fill && (
          <Defs>
            <LinearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={stroke} stopOpacity="0.25" />
              <Stop offset="1" stopColor={stroke} stopOpacity="0" />
            </LinearGradient>
          </Defs>
        )}

        {/* Y-axis gridlines + labels */}
        {showScale && yTicks.map((t, i) => (
          <React.Fragment key={i}>
            <Line
              x1={offsetX} y1={t.y} x2={offsetX + plotW} y2={t.y}
              stroke={theme.colors.border} strokeWidth={0.5} strokeDasharray="3,3"
            />
            <SvgText
              x={offsetX - 4} y={t.y + 3.5}
              textAnchor="end" fontSize={9}
              fill={theme.colors.textMuted}
            >
              {fmt(t.v)}
            </SvgText>
          </React.Fragment>
        ))}

        {/* Y-axis line */}
        {showScale && (
          <Line x1={offsetX} y1={0} x2={offsetX} y2={plotH} stroke={theme.colors.border} strokeWidth={0.5} />
        )}

        {fill && <Polygon points={fillPoints} fill="url(#sparkFill)" />}
        <Polyline points={points} fill="none" stroke={stroke} strokeWidth={1.5} />

        {/* X-axis date labels */}
        {showScale && xTicks.map((t, i) => (
          <SvgText
            key={i} x={t.x} y={plotH + X_LABEL_H - 3}
            textAnchor={i === 0 ? 'start' : i === xTicks.length - 1 ? 'end' : 'middle'}
            fontSize={9} fill={theme.colors.textMuted}
          >
            {t.label}
          </SvgText>
        ))}
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
