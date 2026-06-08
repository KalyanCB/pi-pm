import { useQuery } from '@tanstack/react-query';
import { useApi } from '../ApiProvider';
import { queryKeys } from '../queryKeys';
import { useAuthStore } from '../stores/authStore';

export function useStocksQuery() {
  const api = useApi();
  const isAuthenticated = useAuthStore((s) => s.status === 'authenticated');

  return useQuery({
    queryKey: queryKeys.stocks.list(),
    queryFn: () => api.stocks.list(),
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 30,
  });
}

export function useStockSymbolMap() {
  const { data, isLoading } = useStocksQuery();
  const map = new Map<string, string>();
  if (data) {
    for (const stock of data) {
      map.set(stock.id, stock.symbol);
    }
  }
  return { symbolMap: map, isLoading };
}
