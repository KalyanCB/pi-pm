import React from 'react';
import { MetricCard } from '../../layout/MetricCard';
import { MetricValue } from '../../atoms/MetricValue';
import { SparklineChart } from '../../charts/SparklineChart';

export interface AlphaCardProps {
  alpha: number | null;
  series: number[];
}

export function AlphaCard({ alpha, series }: AlphaCardProps) {
  return (
    <MetricCard
      label="ALPHA vs NIFTY (CUM)"
      footer={<SparklineChart data={series} color="#3dba7a" />}
    >
      <MetricValue value={alpha} format="percent" colorize size="lg" />
    </MetricCard>
  );
}
