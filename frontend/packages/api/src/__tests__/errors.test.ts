import { ApiError, normalizeError, shouldRetry, retryDelay, ReconciliationGateError } from '../errors';

describe('normalizeError', () => {
  it('maps 404 to NOT_FOUND', () => {
    const err = normalizeError(404, { detail: 'Not found' });
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.code).toBe('NOT_FOUND');
    expect(err.message).toBe('Not found');
  });

  it('maps 409 to ReconciliationGateError', () => {
    const err = normalizeError(409, { detail: 'gate' });
    expect(err).toBeInstanceOf(ReconciliationGateError);
    expect(err.code).toBe('RECONCILIATION_GATE');
  });
});

describe('shouldRetry', () => {
  it('retries 500', () => {
    expect(shouldRetry(500)).toBe(true);
  });

  it('does not retry 409', () => {
    expect(shouldRetry(409)).toBe(false);
  });

  it('does not retry 404', () => {
    expect(shouldRetry(404)).toBe(false);
  });
});

describe('retryDelay', () => {
  it('exponential backoff capped at 8s', () => {
    expect(retryDelay(0)).toBe(1000);
    expect(retryDelay(1)).toBe(2000);
    expect(retryDelay(10)).toBe(8000);
  });
});
