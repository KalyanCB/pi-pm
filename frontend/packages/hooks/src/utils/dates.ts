export function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function defaultStrategyName(): string {
  return process.env.EXPO_PUBLIC_DEFAULT_STRATEGY ?? 'momentum_v1';
}

// Re-export for UI convenience
export { defaultStrategyName as getDefaultStrategy };
