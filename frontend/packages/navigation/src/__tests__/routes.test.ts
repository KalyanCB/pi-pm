import { Routes, NAV_ITEMS } from '../routes';
import { buildCopilotLink, buildRecommendationLink } from '../deepLinks';
import { resolveCitationRoute } from '../citationNavigation';

describe('Routes', () => {
  it('defines primary nav items', () => {
    expect(NAV_ITEMS.length).toBeGreaterThanOrEqual(5);
    expect(Routes.dashboard).toBe('/');
  });

  it('builds recommendation deep link', () => {
    expect(buildRecommendationLink('RELIANCE')).toBe('/recommendations/RELIANCE');
  });

  it('builds copilot link with query', () => {
    expect(buildCopilotLink('Why BUY?')).toBe('/copilot?q=Why%20BUY%3F');
  });
});

describe('resolveCitationRoute', () => {
  it('resolves recommendation_results', () => {
    expect(
      resolveCitationRoute({
        ref: '1',
        source_table: 'recommendation_results',
        source_field: 'action',
        source_value: 'INFY',
      }),
    ).toBe('/recommendations/INFY');
  });

  it('returns null for unknown table', () => {
    expect(
      resolveCitationRoute({
        ref: '1',
        source_table: 'unknown',
        source_field: null,
        source_value: null,
      }),
    ).toBeNull();
  });
});
