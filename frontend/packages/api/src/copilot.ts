import type { AskRequest, AskResponse } from '@pipm/types';
import type { ApiClient } from './client';

export function createCopilotApi(client: ApiClient) {
  return {
    ask(body: AskRequest) {
      return client.post<AskResponse>('/copilot/ask', {
        question: body.question,
        session_id: body.session_id ?? null,
      });
    },
    getAudit(limit = 50) {
      return client.get<
        Array<{
          id: string;
          question: string;
          intent: string;
          refused: boolean;
          answer: string | null;
          created_at: string;
        }>
      >('/copilot/audit', { params: { limit } });
    },
  };
}

export type CopilotApi = ReturnType<typeof createCopilotApi>;
