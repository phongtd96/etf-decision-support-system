import { apiClient } from "./client";
import type { ETFPriceHistoryResponse } from "../types/etf";

export async function fetchETFPrices(
  symbol: string,
  days = 252,
): Promise<ETFPriceHistoryResponse> {
  const response = await apiClient.get<ETFPriceHistoryResponse>(
    `/api/etfs/${symbol}/prices`,
    {
      params: { days },
    },
  );
  return response.data;
}
