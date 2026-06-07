import React from 'react';
import { useLocalSearchParams } from 'expo-router';
import { RecommendationDetailScreen } from '@pipm/ui';

export default function RecommendationDetailRoute() {
  const { symbol, runId } = useLocalSearchParams<{ symbol: string; runId?: string }>();
  return <RecommendationDetailScreen symbol={symbol ?? ''} runId={runId} />;
}
