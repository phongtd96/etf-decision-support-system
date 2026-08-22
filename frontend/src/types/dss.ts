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

export interface SensitivityComparisonRow {
  symbol: string;
  balanced_score: number;
  balanced_rank: number;
  growth_score: number;
  growth_rank: number;
  growth_rank_change: number;
  risk_averse_score: number;
  risk_averse_rank: number;
  risk_averse_rank_change: number;
}

export interface SensitivityStabilitySummary {
  top_etf_stable: boolean;
  max_absolute_rank_change: number;
  growth_changed_count: number;
  risk_averse_changed_count: number;
}

export interface DSSSensitivityResponse {
  as_of_date: string;
  profiles: Record<string, Record<string, number>>;
  comparisons: SensitivityComparisonRow[];
  stability_summary: SensitivityStabilitySummary;
}
