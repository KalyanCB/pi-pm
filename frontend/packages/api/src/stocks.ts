import type { StockRead } from '@pipm/types';
import type { ApiClient } from './client';

export function createStocksApi(client: ApiClient) {
  return {
    list(dataStatus?: string) {
      return client.get<StockRead[]>('/stocks', {
        params: { data_status: dataStatus },
      });
    },
    get(symbol: string) {
      return client.get<StockRead>(`/stocks/${symbol}`);
    },
  };
}

export type StocksApi = ReturnType<typeof createStocksApi>;
