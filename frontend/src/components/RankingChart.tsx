import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DSSRankingItem } from "../types/dss";
import { formatSmartScore } from "../utils/formatters";

interface RankingChartProps {
  rankings: DSSRankingItem[];
}

export function RankingChart({ rankings }: RankingChartProps) {
  const chartData = rankings.map((item) => ({
    symbol: item.symbol,
    score: Number(item.smart_score.toFixed(2)),
  }));

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>SMART Ranking</h2>
          <p>Higher scores indicate stronger relative performance under the SMART method.</p>
        </div>
      </div>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 18, right: 28 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} tickLine={false} />
            <YAxis
              type="category"
              dataKey="symbol"
              width={92}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(value) => [formatSmartScore(Number(value)), "SMART score"]}
              cursor={{ fill: "rgba(15, 23, 42, 0.06)" }}
            />
            <Bar dataKey="score" fill="#2563eb" radius={[0, 6, 6, 0]} barSize={28}>
              <LabelList
                dataKey="score"
                position="right"
                formatter={(value: number) => formatSmartScore(value)}
                fill="#172033"
                fontSize={12}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
