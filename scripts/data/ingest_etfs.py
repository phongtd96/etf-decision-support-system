from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.etf import Etf
from app.services.data_service import (
    DATA_SOURCE,
    fetch_etf_history,
    filter_price_date_range,
    normalize_price_data,
    save_price_history,
    validate_price_data,
)
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
                etf = db_session.scalar(select(Etf).where(Etf.symbol == symbol))
                if etf is None:
                    raise RuntimeError(f"ETF not found after seeding: {symbol}")

                provider_df = fetch_etf_history(symbol=symbol, start_date=START_DATE)
                normalized_df = normalize_price_data(provider_df)
                filtered_df = filter_price_date_range(
                    normalized_df,
                    start_date=START_DATE,
                )
                validate_price_data(filtered_df)
                stats = save_price_history(
                    db_session=db_session,
                    etf=etf,
                    df=filtered_df,
                    data_source=DATA_SOURCE,
                )
                db_session.commit()

                total_processed += stats.processed_rows
                summary_rows.append(
                    (symbol, len(provider_df), stats.processed_rows, "OK")
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
