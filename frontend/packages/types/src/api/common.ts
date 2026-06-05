export interface ApiErrorBody {
  detail?: string | { msg: string }[];
  code?: string;
  message?: string;
}

export interface DateRange {
  from?: string;
  to?: string;
}

export interface RiskAlert {
  code: string;
  level: string;
  message: string;
  details?: Record<string, unknown>;
}
