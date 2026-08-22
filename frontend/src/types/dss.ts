export interface CriterionDetail {
  raw_value: number;
  utility: number;
  weight: number;
  weighted_contribution: number;
  criterion_type: string;
}

export interface DSSRankingItem {
  rank: number;
  symbol: string;
  smart_score: number;
  criteria: Record<string, CriterionDetail>;
  reasons: string[];
}

export interface DSSRankingResponse {
  as_of_date: string;
  methodology: string;
  weights: Record<string, number>;
  rankings: DSSRankingItem[];
}
