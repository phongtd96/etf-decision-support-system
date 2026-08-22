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
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.etf import Etf


SUPPORTED_ETFS = [
    {"symbol": "E1VFVN30", "name": "DCVFMVN30 ETF"},
    {"symbol": "FUEVFVND", "name": "DCVFMVN DIAMOND ETF"},
    {"symbol": "FUEVN100", "name": "VINACAPITAL VN100 ETF"},
    {"symbol": "FUEDCMID", "name": "DCVFMVN MID CAP ETF"},
    {"symbol": "FUESSVFL", "name": "SSIAM VNFIN LEAD ETF"},
]


def ensure_supported_etfs(db_session: Session) -> int:
    symbols = [item["symbol"] for item in SUPPORTED_ETFS]
    existing_symbols = set(
        db_session.scalars(select(Etf.symbol).where(Etf.symbol.in_(symbols))).all()
    )

    created_count = 0
    for item in SUPPORTED_ETFS:
        if item["symbol"] in existing_symbols:
            continue

        db_session.add(Etf(symbol=item["symbol"], name=item["name"]))
        created_count += 1

    db_session.commit()
    return created_count


def main() -> None:
    with SessionLocal() as db_session:
        created_count = ensure_supported_etfs(db_session)

    print(f"ETF seed complete. Created {created_count} new ETF record(s).")


if __name__ == "__main__":
    main()
