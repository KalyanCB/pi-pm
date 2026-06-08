import React from 'react';
import type { RiskLevel } from '@pipm/types';
import type { RiskAlert } from '@pipm/types';
import { MetricCard } from '../../layout/MetricCard';
import { RiskIndicator } from '../RiskIndicator';

export interface RiskCardProps {
  riskLevel: RiskLevel;
  alerts: RiskAlert[];
  onPress?: () => void;
}

export function RiskCard({ riskLevel, alerts, onPress }: RiskCardProps) {
  return (
    <MetricCard label="RISK" onPress={onPress} style={{ minWidth: 200, flex: 1 }}>
      <RiskIndicator riskLevel={riskLevel} alerts={alerts} maxAlerts={2} />
    </MetricCard>
  );
}
