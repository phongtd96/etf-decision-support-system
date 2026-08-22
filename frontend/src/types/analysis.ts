export interface TechnicalIndicatorValues {
  sma_20: number | null;
  sma_50: number | null;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  volatility_20: number | null;
}

export interface TechnicalAnalysisResponse {
  symbol: string;
  date: string;
  technical_score: number;
  technical_signal: "BULLISH" | "NEUTRAL" | "BEARISH";
  indicators: TechnicalIndicatorValues;
  reasons: string[];
}
