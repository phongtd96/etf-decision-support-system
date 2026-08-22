import { apiClient } from "./client";
import type { MarketDataUpdateResponse } from "../types/dataUpdate";

export async function updateMarketData(): Promise<MarketDataUpdateResponse> {
  const response = await apiClient.post<MarketDataUpdateResponse>("/api/data/update");
  return response.data;
}
