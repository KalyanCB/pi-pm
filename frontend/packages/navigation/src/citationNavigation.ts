import { Routes } from './routes';
import type { Citation } from '@pipm/types';

export function resolveCitationRoute(citation: Citation): string | null {
  const table = citation.source_table;
  if (!table) return null;

  switch (table) {
    case 'recommendation_results':
    case 'ranking_results':
      return citation.source_value
        ? Routes.recommendationDetail(citation.source_value)
        : Routes.recommendations;
    case 'investment_review_packets':
    case 'committee_reviews':
    case 'cro_reviews':
      return citation.source_value
        ? `/committee/${citation.source_value}`
        : Routes.committee;
    case 'portfolio_positions':
      return citation.source_value
        ? `/portfolio/positions/${citation.source_value}`
        : Routes.portfolio;
    case 'portfolio_exit_recommendations':
      return Routes.exits;
    case 'portfolio_nav_history':
      return `${Routes.portfolio}?section=performance`;
    default:
      return null;
  }
}
