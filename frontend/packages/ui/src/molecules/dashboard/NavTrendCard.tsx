import React from 'react';
import { MetricCard } from '../../layout/MetricCard';
import { MetricValue } from '../../atoms/MetricValue';
import { SparklineChart } from '../../charts/SparklineChart';

export interface NavTrendCardProps {
  nav: number | null;
  series: number[];
}

export function NavTrendCard({ nav, series }: NavTrendCardProps) {
  return (
    <MetricCard
      label="NAV TREND"
      footer={<SparklineChart data={series} />}
      style={{ minWidth: 200, flex: 1 }}
    >
      <MetricValue value={nav} format="currency" size="lg" />
    </MetricCard>
  );
}
