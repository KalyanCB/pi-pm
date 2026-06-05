export interface Citation {
  ref: string;
  source_table: string | null;
  source_field: string | null;
  source_value: string | null;
}

export interface AskRequest {
  question: string;
  session_id?: string | null;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  uncited_claims: string[];
  intent: string;
  refused: boolean;
  model: string | null;
  latency_ms: number | null;
  query_log_id: string;
}

export interface CopilotMessageModel {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  refused?: boolean;
  citations?: Citation[];
  uncitedClaims?: string[];
  latencyMs?: number;
}
