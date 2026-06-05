import type { ApiErrorBody } from '@pipm/types';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class ReconciliationGateError extends ApiError {
  constructor(details?: Record<string, unknown>) {
    super(
      409,
      'RECONCILIATION_GATE',
      'Analytics unavailable — reconciliation failed',
      details,
    );
    this.name = 'ReconciliationGateError';
  }
}

function extractMessage(body: ApiErrorBody, status: number): string {
  if (typeof body.detail === 'string') return body.detail;
  if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  if (body.message) return body.message;
  return `Request failed with status ${status}`;
}

export function normalizeError(status: number, body: unknown): ApiError {
  const parsed = (body ?? {}) as ApiErrorBody;
  const message = extractMessage(parsed, status);
  const code = parsed.code ?? statusCodeToCode(status);

  if (status === 409) {
    return new ReconciliationGateError(
      typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : undefined,
    );
  }

  return new ApiError(status, code, message);
}

function statusCodeToCode(status: number): string {
  switch (status) {
    case 401:
      return 'UNAUTHORIZED';
    case 403:
      return 'FORBIDDEN';
    case 404:
      return 'NOT_FOUND';
    case 422:
      return 'VALIDATION_ERROR';
    default:
      return status >= 500 ? 'SERVER_ERROR' : 'REQUEST_ERROR';
  }
}

export function shouldRetry(status: number): boolean {
  if (status === 409 || status === 404 || status === 401 || status === 403) return false;
  return status >= 500;
}

export function retryDelay(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, 8000);
}
