export interface StockRead {
  id: string;
  symbol: string;
  name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  is_active: boolean;
  data_status: string;
}
