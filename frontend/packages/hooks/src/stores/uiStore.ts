import { create } from 'zustand';
import { useCopilotStore } from './copilotStore';

type RecommendationTab = 'BUY' | 'WATCH' | 'EXIT_APPROVED';

export interface SelectedRecommendation {
  id: string;
  symbol: string;
  runId: string;
  action: RecommendationTab;
}

interface UiState {
  recommendationTab: RecommendationTab;
  /** ISO date for recommendations screen; null = latest available day */
  recommendationAsOfDate: string | null;
  sidebarCollapsed: boolean;
  copilotPanelOpen: boolean;
  selectedRecommendation: SelectedRecommendation | null;
  setRecommendationTab: (tab: RecommendationTab) => void;
  setRecommendationAsOfDate: (date: string | null) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setCopilotPanelOpen: (open: boolean) => void;
  toggleCopilotPanel: () => void;
  setSelectedRecommendation: (rec: SelectedRecommendation | null) => void;
  openCopilotWithQuestion: (question: string) => void;
}

export const useUiStore = create<UiState>((set, get) => ({
  recommendationTab: 'BUY',
  recommendationAsOfDate: null,
  sidebarCollapsed: false,
  copilotPanelOpen: false,
  selectedRecommendation: null,
  setRecommendationTab: (tab) => set({ recommendationTab: tab }),
  setRecommendationAsOfDate: (date) => set({ recommendationAsOfDate: date }),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setCopilotPanelOpen: (open) => set({ copilotPanelOpen: open }),
  toggleCopilotPanel: () => set({ copilotPanelOpen: !get().copilotPanelOpen }),
  setSelectedRecommendation: (rec) => set({ selectedRecommendation: rec }),
  openCopilotWithQuestion: (question) => {
    useCopilotStore.getState().openPanel({ prefill: question });
    set({ copilotPanelOpen: true });
  },
}));
