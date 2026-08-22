export interface SymbolUpdateSummary {
  symbol: string;
  fetched_rows: number;
  valid_rows: number;
  changed_rows: number;
  latest_date: string | null;
  indicators_recalculated: boolean;
  indicator_rows: number;
  status: string;
  message: string;
}

export interface MarketDataUpdateResponse {
  status: string;
  latest_date: string | null;
  processed_price_rows: number;
  symbols_updated: string[];
  indicators_recalculated: boolean;
  message: string;
  details: SymbolUpdateSummary[];
}
