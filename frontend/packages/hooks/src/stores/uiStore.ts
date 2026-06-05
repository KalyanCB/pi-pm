import { create } from 'zustand';

type RecommendationTab = 'BUY' | 'WATCH' | 'EXIT_APPROVED';

interface UiState {
  recommendationTab: RecommendationTab;
  sidebarCollapsed: boolean;
  setRecommendationTab: (tab: RecommendationTab) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  recommendationTab: 'BUY',
  sidebarCollapsed: false,
  setRecommendationTab: (tab) => set({ recommendationTab: tab }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
}));
