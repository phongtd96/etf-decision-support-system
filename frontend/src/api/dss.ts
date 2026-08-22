import { apiClient } from "./client";
import type {
  DSSRankingItem,
  DSSRankingResponse,
  DSSSensitivityResponse,
} from "../types/dss";

export async function fetchDSSRanking(): Promise<DSSRankingResponse> {
  const response = await apiClient.get<DSSRankingResponse>("/api/dss/ranking");
  return response.data;
}

export async function fetchDSSDetail(symbol: string): Promise<DSSRankingItem> {
  const response = await apiClient.get<DSSRankingItem>(`/api/dss/${symbol}`);
  return response.data;
}

export async function fetchDSSSensitivity(): Promise<DSSSensitivityResponse> {
  const response = await apiClient.get<DSSSensitivityResponse>("/api/dss/sensitivity");
  return response.data;
}
