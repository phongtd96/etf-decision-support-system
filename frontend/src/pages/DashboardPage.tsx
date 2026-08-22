import { useEffect, useState } from "react";

import { updateMarketData } from "../api/dataUpdate";
import { fetchDSSRanking } from "../api/dss";
import { EmptyState } from "../components/EmptyState";
import { RankingChart } from "../components/RankingChart";
import { RankingTable } from "../components/RankingTable";
import { SummaryCards } from "../components/SummaryCards";
import type { DSSRankingResponse } from "../types/dss";

export function DashboardPage() {
  const [data, setData] = useState<DSSRankingResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [updateMessage, setUpdateMessage] = useState<string | null>(null);
  const [updateMessageType, setUpdateMessageType] = useState<"success" | "info" | "error">(
    "info",
  );

  useEffect(() => {
    let isMounted = true;

    loadRanking(() => isMounted);

    return () => {
      isMounted = false;
    };
  }, []);

  async function loadRanking(shouldUpdate = () => true) {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const ranking = await fetchDSSRanking();
      if (shouldUpdate()) {
        setData(ranking);
      }
    } catch {
      if (shouldUpdate()) {
        setErrorMessage(
          "Unable to load SMART ranking. Please check that the FastAPI backend is running.",
        );
      }
    } finally {
      if (shouldUpdate()) {
        setIsLoading(false);
      }
    }
  }

  async function handleUpdateMarketData() {
    try {
      setIsUpdating(true);
      setUpdateMessage(null);
      const summary = await updateMarketData();
      if (summary.status === "already_up_to_date") {
        setUpdateMessage("Data is already up to date.");
        setUpdateMessageType("info");
      } else {
        const updatedSymbols = summary.symbols_updated.join(", ");
        setUpdateMessage(
          `Market data updated. ${summary.processed_price_rows} price row(s) changed${
            updatedSymbols ? ` for ${updatedSymbols}` : ""
          }.`,
        );
        setUpdateMessageType("success");
      }
      await loadRanking();
    } catch {
      setUpdateMessage(
        "Market data update failed. Please check the backend logs and data source availability.",
      );
      setUpdateMessageType("error");
    } finally {
      setIsUpdating(false);
    }
  }

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
      <section className="dashboard-actions">
        <div>
          <h2>Market Data</h2>
          <p>Refresh ETF prices from the configured VCI data source.</p>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={handleUpdateMarketData}
          disabled={isUpdating}
        >
          {isUpdating ? "Updating..." : "Update market data"}
        </button>
      </section>

      {updateMessage && (
        <div className={`update-message ${updateMessageType}`}>{updateMessage}</div>
      )}

      <SummaryCards data={data} />
      <RankingChart rankings={data.rankings} />
      <RankingTable rankings={data.rankings} />
    </div>
  );
}
