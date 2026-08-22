import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DSSRankingItem } from "../types/dss";
import {
  formatInteger,
  formatNullableNumber,
  formatPercent,
  formatSmartScore,
} from "../utils/formatters";

interface SmartBreakdownProps {
  dss: DSSRankingItem;
}

const criteriaLabels: Record<string, string> = {
  technical_momentum: "Technical Momentum",
  return_20d: "Return 20D",
  volatility_20d: "Volatility 20D",
  max_drawdown_60d: "Max Drawdown 60D",
  avg_volume_20d: "Average Volume 20D",
};

export function SmartBreakdown({ dss }: SmartBreakdownProps) {
  const rows = Object.entries(criteriaLabels).map(([key, label]) => ({
    key,
    label,
    detail: dss.criteria[key],
  }));
  const chartData = rows.map((row) => ({
    criterion: row.label,
    contribution: Number(row.detail.weighted_contribution.toFixed(2)),
  }));

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>SMART Breakdown</h2>
          <p>Weighted contributions explain how the backend SMART score is built.</p>
        </div>
      </div>

      <div className="breakdown-grid">
        <div className="table-wrap">
          <table className="ranking-table compact-table">
            <thead>
              <tr>
                <th>Criterion</th>
                <th>Raw Value</th>
                <th>Utility</th>
                <th>Weight</th>
                <th>Contribution</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key}>
                  <td>{row.label}</td>
                  <td>{formatCriterionRawValue(row.key, row.detail.raw_value)}</td>
                  <td>{formatNullableNumber(row.detail.utility)}</td>
                  <td>{formatPercent(row.detail.weight)}</td>
                  <td className="score-cell">
                    {formatSmartScore(row.detail.weighted_contribution)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="contribution-chart">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 40, right: 18 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tickLine={false} />
              <YAxis
                type="category"
                dataKey="criterion"
                width={142}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12 }}
              />
              <Tooltip
                formatter={(value) => [
                  formatSmartScore(Number(value)),
                  "Weighted contribution",
                ]}
              />
              <Bar dataKey="contribution" fill="#2563eb" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}

function formatCriterionRawValue(key: string, value: number): string {
  if (key === "return_20d" || key === "volatility_20d" || key === "max_drawdown_60d") {
    return formatPercent(value);
  }
  if (key === "avg_volume_20d") {
    return formatInteger(value);
  }
  return formatSmartScore(value);
}
