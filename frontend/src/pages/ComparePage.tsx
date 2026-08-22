import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchDSSRanking } from "../api/dss";
import { EmptyState } from "../components/EmptyState";
import type { DSSRankingItem, DSSRankingResponse } from "../types/dss";
import {
  criterionKeys,
  criterionLabels,
  formatCriterionRawValue,
} from "../utils/criteria";
import { formatDisplayDate, formatSmartScore } from "../utils/formatters";

export function ComparePage() {
  const [data, setData] = useState<DSSRankingResponse | null>(null);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadRanking() {
      try {
        setIsLoading(true);
        setErrorMessage(null);
        const ranking = await fetchDSSRanking();
        if (isMounted) {
          setData(ranking);
          setSelectedSymbols(ranking.rankings.slice(0, 3).map((item) => item.symbol));
        }
      } catch {
        if (isMounted) {
          setErrorMessage(
            "Unable to load ETF comparison data. Please check that the backend is running.",
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadRanking();

    return () => {
      isMounted = false;
    };
  }, []);

  const selectedItems = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.rankings.filter((item) => selectedSymbols.includes(item.symbol));
  }, [data, selectedSymbols]);

  if (isLoading) {
    return <EmptyState title="Loading comparison" message="Fetching SMART ranking data..." />;
  }

  if (errorMessage) {
    return <EmptyState title="Comparison unavailable" message={errorMessage} />;
  }

  if (!data || data.rankings.length === 0) {
    return (
      <EmptyState
        title="No comparison data"
        message="The backend returned an empty SMART ranking response."
      />
    );
  }

  return (
    <div className="dashboard">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>ETF Comparison</h2>
            <p>
              Select 2 to 5 ETFs. Scores come directly from the backend SMART ranking
              as of {formatDisplayDate(data.as_of_date)}.
            </p>
          </div>
        </div>
        <div className="selector-grid">
          {data.rankings.map((item) => (
            <label className="selector-option" key={item.symbol}>
              <input
                type="checkbox"
                checked={selectedSymbols.includes(item.symbol)}
                onChange={() => toggleSymbol(item.symbol)}
              />
              <span>{item.symbol}</span>
            </label>
          ))}
        </div>
        {selectedItems.length < 2 && (
          <p className="inline-warning">Select at least 2 ETFs to compare.</p>
        )}
      </section>

      {selectedItems.length >= 2 && (
        <>
          <ScoreComparisonChart items={selectedItems} />
          <UtilityComparisonChart items={selectedItems} />
          <ComparisonTable items={selectedItems} />
        </>
      )}
    </div>
  );

  function toggleSymbol(symbol: string) {
    setSelectedSymbols((current) => {
      if (current.includes(symbol)) {
        return current.filter((item) => item !== symbol);
      }
      if (current.length >= 5) {
        return current;
      }
      return [...current, symbol];
    });
  }
}

function ScoreComparisonChart({ items }: { items: DSSRankingItem[] }) {
  const chartData = items.map((item) => ({
    symbol: item.symbol,
    smart_score: Number(item.smart_score.toFixed(2)),
  }));

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>SMART Score Comparison</h2>
          <p>Backend-calculated SMART scores for selected ETFs.</p>
        </div>
      </div>
      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="symbol" tickLine={false} />
            <YAxis domain={[0, 100]} tickLine={false} />
            <Tooltip
              formatter={(value) => [formatSmartScore(Number(value)), "SMART score"]}
            />
            <Bar dataKey="smart_score" fill="#2563eb" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function UtilityComparisonChart({ items }: { items: DSSRankingItem[] }) {
  const chartData = criterionKeys.map((key) => ({
    criterion: criterionLabels[key],
    ...Object.fromEntries(items.map((item) => [item.symbol, item.criteria[key].utility])),
  }));

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Normalized Criterion Utilities</h2>
          <p>Utilities are 0 to 1 values, so criteria with different units can be compared.</p>
        </div>
      </div>
      <div className="price-chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="criterion" tickLine={false} tick={{ fontSize: 12 }} />
            <YAxis domain={[0, 1]} tickLine={false} />
            <Tooltip formatter={(value) => [Number(value).toFixed(2), "Utility"]} />
            <Legend />
            {items.map((item, index) => (
              <Bar
                key={item.symbol}
                dataKey={item.symbol}
                fill={chartColors[index % chartColors.length]}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function ComparisonTable({ items }: { items: DSSRankingItem[] }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Comparison Table</h2>
          <p>Raw criterion values and SMART ranks for the selected ETFs.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table className="ranking-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Symbol</th>
              <th>SMART Score</th>
              <th>Technical Momentum</th>
              <th>Return 20D</th>
              <th>Volatility 20D</th>
              <th>Max Drawdown 60D</th>
              <th>Average Volume 20D</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.symbol}>
                <td>{item.rank}</td>
                <td>{item.symbol}</td>
                <td className="score-cell">{formatSmartScore(item.smart_score)}</td>
                {criterionKeys.map((key) => (
                  <td key={key}>
                    {formatCriterionRawValue(key, item.criteria[key].raw_value)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const chartColors = ["#2563eb", "#0f766e", "#f59e0b", "#7c3aed", "#b42318"];
