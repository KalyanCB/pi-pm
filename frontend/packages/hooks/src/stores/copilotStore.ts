import { create } from 'zustand';
import type { CopilotMessageModel } from '@pipm/types';

interface CopilotState {
  sessionId: string | null;
  messages: CopilotMessageModel[];
  isPanelOpen: boolean;
  prefillQuestion: string | null;
  sourceScreen: string | null;
  openPanel: (opts?: { prefill?: string; source?: string }) => void;
  closePanel: () => void;
  appendMessage: (msg: CopilotMessageModel) => void;
  resetSession: () => void;
}

export const useCopilotStore = create<CopilotState>((set) => ({
  sessionId: null,
  messages: [],
  isPanelOpen: false,
  prefillQuestion: null,
  sourceScreen: null,
  openPanel: (opts) =>
    set({
      isPanelOpen: true,
      prefillQuestion: opts?.prefill ?? null,
      sourceScreen: opts?.source ?? null,
    }),
  closePanel: () => set({ isPanelOpen: false, prefillQuestion: null }),
  appendMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  resetSession: () =>
    set({
      sessionId: null,
      messages: [],
      prefillQuestion: null,
    }),
}));
