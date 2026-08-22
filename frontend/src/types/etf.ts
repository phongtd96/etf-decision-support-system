export interface PriceHistoryPoint {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface ETFPriceHistoryResponse {
  symbol: string;
  prices: PriceHistoryPoint[];
}
