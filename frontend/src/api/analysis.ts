import { apiClient } from "./client";
import type { TechnicalAnalysisResponse } from "../types/analysis";

export async function fetchTechnicalAnalysis(
  symbol: string,
): Promise<TechnicalAnalysisResponse> {
  const response = await apiClient.get<TechnicalAnalysisResponse>(
    `/api/analysis/${symbol}`,
  );
  return response.data;
}
