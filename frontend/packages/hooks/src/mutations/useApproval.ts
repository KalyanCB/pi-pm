import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';

export function useApproveRecommendation() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { resultId: string; decision?: string; note?: string }) =>
      api.recommendations.approve(params.resultId, {
        decision: params.decision ?? 'APPROVED',
        note: params.note ?? null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['recommendations'] });
      void qc.invalidateQueries({ queryKey: ['portfolio'] });
    },
  });
}

export function useRejectRecommendation() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { resultId: string; note?: string }) =>
      api.recommendations.reject(params.resultId, { note: params.note }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useConfirmExit() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (exitId: string) => api.portfolio.confirmExit(exitId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['portfolio'] });
      void qc.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}

export function useRejectExit() {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { exitId: string; reason?: string }) =>
      api.portfolio.rejectExit(params.exitId, params.reason),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['portfolio'] });
      void qc.invalidateQueries({ queryKey: ['recommendations'] });
    },
  });
}
