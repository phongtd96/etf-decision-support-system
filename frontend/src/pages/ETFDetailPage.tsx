import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchTechnicalAnalysis } from "../api/analysis";
import { fetchDSSDetail } from "../api/dss";
import { fetchETFPrices } from "../api/etfs";
import { EmptyState } from "../components/EmptyState";
import { PriceHistoryChart } from "../components/PriceHistoryChart";
import { SmartBreakdown } from "../components/SmartBreakdown";
import { TechnicalIndicators } from "../components/TechnicalIndicators";
import type { TechnicalAnalysisResponse } from "../types/analysis";
import type { DSSRankingItem } from "../types/dss";
import type { ETFPriceHistoryResponse } from "../types/etf";
import {
  formatDisplayDate,
  formatPercent,
  formatSmartScore,
} from "../utils/formatters";

export function ETFDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const normalizedSymbol = symbol?.toUpperCase() ?? "";
  const [dss, setDss] = useState<DSSRankingItem | null>(null);
  const [analysis, setAnalysis] = useState<TechnicalAnalysisResponse | null>(null);
  const [prices, setPrices] = useState<ETFPriceHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDetail() {
      if (!normalizedSymbol) {
        setErrorMessage("ETF symbol is missing.");
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setErrorMessage(null);
        const [dssResponse, analysisResponse, priceResponse] = await Promise.all([
          fetchDSSDetail(normalizedSymbol),
          fetchTechnicalAnalysis(normalizedSymbol),
          fetchETFPrices(normalizedSymbol, 252),
        ]);

        if (isMounted) {
          setDss(dssResponse);
          setAnalysis(analysisResponse);
          setPrices(priceResponse);
        }
      } catch {
        if (isMounted) {
          setErrorMessage(
            `Unable to load ETF detail for ${normalizedSymbol}. Please check the symbol and backend availability.`,
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadDetail();

    return () => {
      isMounted = false;
    };
  }, [normalizedSymbol]);

  if (isLoading) {
    return (
      <EmptyState title="Loading ETF detail" message="Fetching DSS and price data..." />
    );
  }

  if (errorMessage) {
    return <EmptyState title="ETF detail unavailable" message={errorMessage} />;
  }

  if (!dss || !analysis || !prices) {
    return (
      <EmptyState
        title="ETF detail unavailable"
        message="The backend response was incomplete."
      />
    );
  }

  const hasPrices = prices.prices.length > 0;

  return (
    <div className="detail-page">
      <Link to="/" className="back-link">
        Back to Dashboard
      </Link>

      <section className="detail-header">
        <div>
          <h1>{dss.symbol}</h1>
          <p>As-of date: {formatDisplayDate(analysis.date)}</p>
        </div>
      </section>

      <section className="summary-grid detail-summary">
        <article className="summary-card">
          <span>SMART Score</span>
          <strong>{formatSmartScore(dss.smart_score)}</strong>
          <p>SMART rank #{dss.rank}</p>
        </article>
        <article className="summary-card">
          <span>Technical Signal</span>
          <strong>{analysis.technical_signal}</strong>
          <p>Technical score {formatSmartScore(analysis.technical_score)}</p>
        </article>
        <article className="summary-card">
          <span>Return 20D</span>
          <strong>{formatPercent(dss.criteria.return_20d.raw_value)}</strong>
          <p>Raw SMART criterion value</p>
        </article>
        <article className="summary-card">
          <span>Volatility 20D</span>
          <strong>{formatPercent(dss.criteria.volatility_20d.raw_value)}</strong>
          <p>Raw SMART criterion value</p>
        </article>
      </section>

      {hasPrices ? (
        <PriceHistoryChart prices={prices.prices} />
      ) : (
        <EmptyState
          title="No price history"
          message="The backend returned an empty price history for this ETF."
        />
      )}

      <TechnicalIndicators analysis={analysis} />
      <SmartBreakdown dss={dss} />

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Why this ranking?</h2>
            <p>Backend-generated decision-support explanations.</p>
          </div>
        </div>
        <ul className="reason-list">
          {dss.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
