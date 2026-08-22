import type { TechnicalAnalysisResponse } from "../types/analysis";
import {
  formatNullableNumber,
  formatNullablePercent,
  formatSmartScore,
} from "../utils/formatters";

interface TechnicalIndicatorsProps {
  analysis: TechnicalAnalysisResponse;
}

export function TechnicalIndicators({ analysis }: TechnicalIndicatorsProps) {
  const indicators = [
    ["SMA20", formatNullableNumber(analysis.indicators.sma_20)],
    ["SMA50", formatNullableNumber(analysis.indicators.sma_50)],
    ["RSI14", formatNullableNumber(analysis.indicators.rsi_14)],
    ["MACD", formatNullableNumber(analysis.indicators.macd)],
    ["MACD Signal", formatNullableNumber(analysis.indicators.macd_signal)],
    ["Volatility20", formatNullablePercent(analysis.indicators.volatility_20)],
  ];

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Technical Indicators</h2>
          <p>
            Latest backend-calculated indicators and technical score for this ETF.
          </p>
        </div>
      </div>

      <div className="indicator-summary">
        <div>
          <span>Technical Signal</span>
          <strong className={`signal-pill ${analysis.technical_signal.toLowerCase()}`}>
            {analysis.technical_signal}
          </strong>
        </div>
        <div>
          <span>Technical Score</span>
          <strong>{formatSmartScore(analysis.technical_score)}</strong>
        </div>
      </div>

      <div className="indicator-grid">
        {indicators.map(([label, value]) => (
          <div className="indicator-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
