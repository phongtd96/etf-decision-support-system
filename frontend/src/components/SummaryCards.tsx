import type { DSSRankingResponse } from "../types/dss";
import { formatSmartScore } from "../utils/formatters";

interface SummaryCardsProps {
  data: DSSRankingResponse;
}

export function SummaryCards({ data }: SummaryCardsProps) {
  const topEtf = data.rankings[0];

  const cards = [
    {
      label: "Number of ETFs",
      value: data.rankings.length.toString(),
      detail: "Supported Vietnamese ETFs",
    },
    {
      label: "Top-ranked ETF",
      value: topEtf?.symbol ?? "-",
      detail: topEtf ? `SMART ${formatSmartScore(topEtf.smart_score)}` : "No ranking",
    },
    {
      label: "As-of date",
      value: data.as_of_date,
      detail: "Latest ranking date",
    },
    {
      label: "Methodology",
      value: data.methodology,
      detail: "Simple Multi-Attribute Rating Technique",
    },
  ];

  return (
    <section className="summary-grid">
      {cards.map((card) => (
        <article className="summary-card" key={card.label}>
          <span>{card.label}</span>
          <strong>{card.value}</strong>
          <p>{card.detail}</p>
        </article>
      ))}
    </section>
  );
}
