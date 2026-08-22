import { Link } from "react-router-dom";

import type { DSSRankingItem } from "../types/dss";
import {
  formatInteger,
  formatPercent,
  formatSmartScore,
} from "../utils/formatters";

interface RankingTableProps {
  rankings: DSSRankingItem[];
}

export function RankingTable({ rankings }: RankingTableProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Ranking Details</h2>
          <p>Raw criterion values used by the SMART decision-support model.</p>
        </div>
      </div>

      <div className="table-wrap">
        <table className="ranking-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>ETF</th>
              <th>SMART Score</th>
              <th>Technical Momentum</th>
              <th>Return 20D</th>
              <th>Volatility 20D</th>
              <th>Max Drawdown 60D</th>
              <th>Average Volume 20D</th>
            </tr>
          </thead>
          <tbody>
            {rankings.map((item) => (
              <tr key={item.symbol}>
                <td>{item.rank}</td>
                <td>
                  <Link to={`/etf/${item.symbol}`} className="symbol-link">
                    {item.symbol}
                  </Link>
                </td>
                <td className="score-cell">{formatSmartScore(item.smart_score)}</td>
                <td>{formatSmartScore(item.criteria.technical_momentum.raw_value)}</td>
                <td>{formatPercent(item.criteria.return_20d.raw_value)}</td>
                <td>{formatPercent(item.criteria.volatility_20d.raw_value)}</td>
                <td>{formatPercent(item.criteria.max_drawdown_60d.raw_value)}</td>
                <td>{formatInteger(item.criteria.avg_volume_20d.raw_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
