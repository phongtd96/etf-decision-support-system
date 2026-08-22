import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { PriceHistoryPoint } from "../types/etf";
import { formatDisplayDate, formatNullableNumber } from "../utils/formatters";

interface PriceHistoryChartProps {
  prices: PriceHistoryPoint[];
}

interface ChartPoint {
  date: string;
  displayDate: string;
  close: number | null;
  sma20: number | null;
  sma50: number | null;
}

export function PriceHistoryChart({ prices }: PriceHistoryChartProps) {
  const chartData = buildChartData(prices);

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Price History</h2>
          <p>Latest close price with frontend-derived SMA20 and SMA50 overlays.</p>
        </div>
      </div>

      <div className="price-chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ left: 8, right: 24, top: 8 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="displayDate"
              tickLine={false}
              minTickGap={32}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickLine={false}
              tick={{ fontSize: 12 }}
              width={72}
            />
            <Tooltip
              formatter={(value, name) => [
                formatNullableNumber(Number(value)),
                labelForSeries(String(name)),
              ]}
              labelFormatter={(_, payload) =>
                payload?.[0]?.payload?.date
                  ? formatDisplayDate(payload[0].payload.date)
                  : ""
              }
            />
            <Line
              type="monotone"
              dataKey="close"
              name="close"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="sma20"
              name="sma20"
              stroke="#0f766e"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="sma50"
              name="sma50"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function buildChartData(prices: PriceHistoryPoint[]): ChartPoint[] {
  return prices.map((price, index) => ({
    date: price.date,
    displayDate: formatDisplayDate(price.date),
    close: price.close,
    sma20: movingAverage(prices, index, 20),
    sma50: movingAverage(prices, index, 50),
  }));
}

function movingAverage(
  prices: PriceHistoryPoint[],
  currentIndex: number,
  windowSize: number,
): number | null {
  const startIndex = currentIndex - windowSize + 1;
  if (startIndex < 0) {
    return null;
  }

  const closeValues = prices
    .slice(startIndex, currentIndex + 1)
    .map((price) => price.close);
  if (closeValues.some((value) => value === null)) {
    return null;
  }

  const values = closeValues as number[];
  const total = values.reduce((sum, value) => sum + value, 0);
  return Number((total / windowSize).toFixed(2));
}

function labelForSeries(name: string): string {
  if (name === "sma20") {
    return "SMA20";
  }
  if (name === "sma50") {
    return "SMA50";
  }
  return "Close";
}
