import { useEffect, useState } from "react";

import { fetchDSSRanking } from "../api/dss";
import { EmptyState } from "../components/EmptyState";
import { RankingChart } from "../components/RankingChart";
import { RankingTable } from "../components/RankingTable";
import { SummaryCards } from "../components/SummaryCards";
import type { DSSRankingResponse } from "../types/dss";

export function DashboardPage() {
  const [data, setData] = useState<DSSRankingResponse | null>(null);
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
        }
      } catch {
        if (isMounted) {
          setErrorMessage(
            "Unable to load SMART ranking. Please check that the FastAPI backend is running.",
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

  if (isLoading) {
    return <EmptyState title="Loading dashboard" message="Fetching SMART ranking data..." />;
  }

  if (errorMessage) {
    return <EmptyState title="Backend unavailable" message={errorMessage} />;
  }

  if (!data || data.rankings.length === 0) {
    return (
      <EmptyState
        title="No ranking data available"
        message="The backend returned an empty SMART ranking response."
      />
    );
  }

  return (
    <div className="dashboard">
      <SummaryCards data={data} />
      <RankingChart rankings={data.rankings} />
      <RankingTable rankings={data.rankings} />
    </div>
  );
}
