import { QueryClient } from '@tanstack/react-query';
import { shouldRetry, retryDelay } from '@pipm/api';
import { ApiError } from '@pipm/api';

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        gcTime: 30 * 60 * 1000,
        refetchOnWindowFocus: true,
        retry: (failureCount, error) => {
          if (error instanceof ApiError) {
            return shouldRetry(error.status) && failureCount < 3;
          }
          return failureCount < 3;
        },
        retryDelay: (attempt) => retryDelay(attempt),
      },
      mutations: {
        retry: false,
      },
    },
  });
}
