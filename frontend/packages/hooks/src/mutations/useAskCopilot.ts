import { useMutation } from '@tanstack/react-query';
import type { AskResponse } from '@pipm/types';
import { useApi } from '../ApiProvider';
import { useCopilotStore } from '../stores/copilotStore';

function newSessionId(): string {
  return crypto.randomUUID?.() ?? `sess-${Date.now()}`;
}

export function useAskCopilot() {
  const api = useApi();
  const appendMessage = useCopilotStore((s) => s.appendMessage);

  return useMutation({
    mutationFn: async (question: string) => {
      let sessionId = useCopilotStore.getState().sessionId;
      if (!sessionId) {
        sessionId = newSessionId();
        useCopilotStore.setState({ sessionId });
      }
      return api.copilot.ask({ question, session_id: sessionId });
    },
    onMutate: (question) => {
      appendMessage({
        id: `user-${Date.now()}`,
        role: 'user',
        content: question,
      });
    },
    onSuccess: (response: AskResponse) => {
      appendMessage({
        id: response.query_log_id,
        role: 'assistant',
        content: response.answer,
        intent: response.intent,
        refused: response.refused,
        citations: response.citations,
        uncitedClaims: response.uncited_claims,
        latencyMs: response.latency_ms ?? undefined,
        lineage: response.lineage ?? undefined,
      });
    },
  });
}
