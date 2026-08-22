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

import { fetchDSSSensitivity } from "../api/dss";
import { EmptyState } from "../components/EmptyState";
import type { DSSSensitivityResponse, SensitivityComparisonRow } from "../types/dss";
import { criterionLabels } from "../utils/criteria";
import {
  formatDisplayDate,
  formatPercent,
  formatSmartScore,
} from "../utils/formatters";

export function SensitivityPage() {
  const [data, setData] = useState<DSSSensitivityResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSensitivity() {
      try {
        setIsLoading(true);
        setErrorMessage(null);
        const sensitivity = await fetchDSSSensitivity();
        if (isMounted) {
          setData(sensitivity);
        }
      } catch {
        if (isMounted) {
          setErrorMessage(
            "Unable to load SMART sensitivity data. Please check that the backend is running.",
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadSensitivity();

    return () => {
      isMounted = false;
    };
  }, []);

  const importantChanges = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.comparisons
      .flatMap((item) => [
        changeText(item, "Growth", item.balanced_rank, item.growth_rank),
        changeText(item, "Risk-Averse", item.balanced_rank, item.risk_averse_rank),
      ])
      .filter((value): value is string => Boolean(value));
  }, [data]);

  if (isLoading) {
    return (
      <EmptyState title="Loading sensitivity" message="Fetching SMART scenarios..." />
    );
  }

  if (errorMessage) {
    return <EmptyState title="Sensitivity unavailable" message={errorMessage} />;
  }

  if (!data || data.comparisons.length === 0) {
    return (
      <EmptyState
        title="No sensitivity data"
        message="The backend returned an empty sensitivity response."
      />
    );
  }

  return (
    <div className="dashboard">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>SMART Sensitivity Analysis</h2>
            <p>
              Sensitivity analysis applies different decision-maker preference profiles
              to the same normalized utilities as of {formatDisplayDate(data.as_of_date)}.
            </p>
          </div>
        </div>
      </section>

      <section className="summary-grid profile-grid">
        {Object.entries(data.profiles).map(([name, weights]) => (
          <article className="summary-card" key={name}>
            <span>{profileLabel(name)}</span>
            <strong>{profileFocus(name)}</strong>
            <ul className="weight-list">
              {Object.entries(weights).map(([criterion, weight]) => (
                <li key={criterion}>
                  <span>{criterionLabels[criterion]}</span>
                  <b>{formatPercent(weight)}</b>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <SensitivityScoreChart rows={data.comparisons} />
      <SensitivityTable rows={data.comparisons} />

      <section className="summary-grid">
        <article className="summary-card">
          <span>Top ETF stable</span>
          <strong>{data.stability_summary.top_etf_stable ? "Yes" : "No"}</strong>
          <p>Same #1 ETF across all scenarios</p>
        </article>
        <article className="summary-card">
          <span>Max rank change</span>
          <strong>{data.stability_summary.max_absolute_rank_change}</strong>
          <p>Largest absolute movement observed</p>
        </article>
        <article className="summary-card">
          <span>Growth changes</span>
          <strong>{data.stability_summary.growth_changed_count}</strong>
          <p>ETFs whose rank changes</p>
        </article>
        <article className="summary-card">
          <span>Risk-Averse changes</span>
          <strong>{data.stability_summary.risk_averse_changed_count}</strong>
          <p>ETFs whose rank changes</p>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Notable Rank Changes</h2>
            <p>These observations describe preference sensitivity, not investment advice.</p>
          </div>
        </div>
        {importantChanges.length > 0 ? (
          <ul className="reason-list">
            {importantChanges.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="muted-text">No rank changes were observed across scenarios.</p>
        )}
      </section>
    </div>
  );
}

function SensitivityScoreChart({ rows }: { rows: SensitivityComparisonRow[] }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Scenario Score Comparison</h2>
          <p>SMART scores under Balanced, Growth, and Risk-Averse profiles.</p>
        </div>
      </div>
      <div className="price-chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="symbol" tickLine={false} />
            <YAxis domain={[0, 100]} tickLine={false} />
            <Tooltip formatter={(value) => [formatSmartScore(Number(value)), "Score"]} />
            <Legend />
            <Bar dataKey="balanced_score" name="Balanced" fill="#2563eb" />
            <Bar dataKey="growth_score" name="Growth" fill="#0f766e" />
            <Bar dataKey="risk_averse_score" name="Risk-Averse" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function SensitivityTable({ rows }: { rows: SensitivityComparisonRow[] }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Ranking Comparison</h2>
          <p>Rank change = Balanced rank minus scenario rank.</p>
        </div>
      </div>
      <div className="table-wrap">
        <table className="ranking-table compact-table">
          <thead>
            <tr>
              <th>ETF</th>
              <th>Balanced</th>
              <th>Growth</th>
              <th>Growth Change</th>
              <th>Risk-Averse</th>
              <th>Risk-Averse Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.symbol}>
                <td>{row.symbol}</td>
                <td>
                  #{row.balanced_rank} / {formatSmartScore(row.balanced_score)}
                </td>
                <td>
                  #{row.growth_rank} / {formatSmartScore(row.growth_score)}
                </td>
                <td className={rankChangeClass(row.growth_rank_change)}>
                  {formatRankChange(row.growth_rank_change)}
                </td>
                <td>
                  #{row.risk_averse_rank} / {formatSmartScore(row.risk_averse_score)}
                </td>
                <td className={rankChangeClass(row.risk_averse_rank_change)}>
                  {formatRankChange(row.risk_averse_rank_change)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function profileLabel(name: string): string {
  return name.replace("_", "-");
}

function profileFocus(name: string): string {
  if (name === "GROWTH") {
    return "Return Focus";
  }
  if (name === "RISK_AVERSE") {
    return "Risk Focus";
  }
  return "Balanced";
}

function formatRankChange(value: number): string {
  if (value > 0) {
    return `+${value}`;
  }
  return value.toString();
}

function rankChangeClass(value: number): string {
  if (value > 0) {
    return "rank-up";
  }
  if (value < 0) {
    return "rank-down";
  }
  return "";
}

function changeText(
  item: SensitivityComparisonRow,
  scenario: string,
  balancedRank: number,
  scenarioRank: number,
): string | null {
  if (balancedRank === scenarioRank) {
    return null;
  }
  return `${item.symbol} moves from rank ${balancedRank} to rank ${scenarioRank} under ${scenario} preferences.`;
}
