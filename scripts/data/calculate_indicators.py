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
from app.services.analysis_service import (
    calculate_technical_indicators,
    load_price_history,
    save_technical_indicators,
)
from scripts.data.seed_etfs import SUPPORTED_ETFS


def main() -> None:
    total_processed = 0
    summary_rows: list[tuple[str, int, str]] = []

    with SessionLocal() as db_session:
        for item in SUPPORTED_ETFS:
            symbol = item["symbol"]

            try:
                etf = db_session.scalar(select(Etf).where(Etf.symbol == symbol))
                if etf is None:
                    raise RuntimeError(f"ETF not found: {symbol}")

                price_df = load_price_history(db_session, symbol)
                indicators_df = calculate_technical_indicators(price_df)
                stats = save_technical_indicators(db_session, etf, indicators_df)
                db_session.commit()

                total_processed += stats.processed_rows
                summary_rows.append((symbol, stats.processed_rows, "OK"))
            except Exception as exc:
                db_session.rollback()
                summary_rows.append((symbol, 0, f"ERROR: {exc}"))

    print("Technical indicator calculation")
    print("-------------------------------")
    for symbol, row_count, status in summary_rows:
        print(f"{symbol:<10} rows={row_count:<6} status={status}")
    print()
    print(f"Total processed: {total_processed}")


if __name__ == "__main__":
    main()
