import { Routes } from './routes';

export function parseDeepLink(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return normalized;
}

export function buildRecommendationLink(symbol: string): string {
  return Routes.recommendationDetail(symbol);
}

export function buildCopilotLink(question?: string): string {
  if (!question) return Routes.copilot;
  return `${Routes.copilot}?q=${encodeURIComponent(question)}`;
}
