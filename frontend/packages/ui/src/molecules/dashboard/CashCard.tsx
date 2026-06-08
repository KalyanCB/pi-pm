import React from 'react';
import { MetricCard } from '../../layout/MetricCard';
import { MetricValue } from '../../atoms/MetricValue';

export interface CashCardProps {
  cashPct: number | null;
}

export function CashCard({ cashPct }: CashCardProps) {
  return (
    <MetricCard label="CASH %">
      <MetricValue value={cashPct} format="percent" size="lg" />
    </MetricCard>
  );
}
