import {
  formatInteger,
  formatPercent,
  formatSmartScore,
} from "./formatters";

export const criterionLabels: Record<string, string> = {
  technical_momentum: "Technical Momentum",
  return_20d: "Return 20D",
  volatility_20d: "Volatility 20D",
  max_drawdown_60d: "Max Drawdown 60D",
  avg_volume_20d: "Average Volume 20D",
};

export const criterionKeys = Object.keys(criterionLabels);

export function formatCriterionRawValue(key: string, value: number): string {
  if (key === "return_20d" || key === "volatility_20d" || key === "max_drawdown_60d") {
    return formatPercent(value);
  }
  if (key === "avg_volume_20d") {
    return formatInteger(value);
  }
  return formatSmartScore(value);
}
