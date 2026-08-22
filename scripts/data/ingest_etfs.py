from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.market_data_update_service import ingest_all_price_history
from scripts.data.seed_etfs import SUPPORTED_ETFS, ensure_supported_etfs


START_DATE = "2022-01-01"


def main() -> None:
    total_processed = 0
    summary_rows: list[tuple[str, int, int, str]] = []

    with SessionLocal() as db_session:
        ensure_supported_etfs(db_session)

        for item in SUPPORTED_ETFS:
            symbol = item["symbol"]

            try:
                summaries = ingest_all_price_history(
                    db_session,
                    start_date=START_DATE,
                    symbols=[symbol],
                )
                db_session.commit()
                summary = summaries[0]

                total_processed += summary.changed_rows
                summary_rows.append(
                    (symbol, summary.fetched_rows, summary.changed_rows, "OK")
                )
            except Exception as exc:
                db_session.rollback()
                summary_rows.append((symbol, 0, 0, f"ERROR: {exc}"))

    print("ETF ingestion summary")
    print("---------------------")
    for symbol, fetched_rows, processed_rows, status in summary_rows:
        print(
            f"{symbol:<10} fetched={fetched_rows:<6} "
            f"processed={processed_rows:<6} status={status}"
        )
    print()
    print(f"Total processed: {total_processed}")


if __name__ == "__main__":
    main()
