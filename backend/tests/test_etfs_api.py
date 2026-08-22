from datetime import date

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.routes import etfs as etfs_route
from app.main import app
from app.services.etf_service import ETFNotFoundError, ETFPriceHistory, PriceHistoryPoint


class ReadOnlyFakeSession:
    def add(self, value):
        raise AssertionError("ETF price endpoint must not add database rows.")

    def delete(self, value):
        raise AssertionError("ETF price endpoint must not delete database rows.")

    def commit(self):
        raise AssertionError("ETF price endpoint must not commit database changes.")

    def flush(self):
        raise AssertionError("ETF price endpoint must not flush database changes.")


def override_db() -> ReadOnlyFakeSession:
    return ReadOnlyFakeSession()


def test_price_history_endpoint_valid_etf(monkeypatch) -> None:
    def fake_get_etf_price_history(db_session, symbol: str, days: int | None = None):
        return ETFPriceHistory(
            symbol=symbol.upper(),
            prices=[
                PriceHistoryPoint(date(2026, 8, 20), 10.0, 11.0, 9.5, 10.5, 1000),
                PriceHistoryPoint(date(2026, 8, 21), 10.5, 12.0, 10.0, 11.5, 1200),
            ],
        )

    monkeypatch.setattr(etfs_route, "get_etf_price_history", fake_get_etf_price_history)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/etfs/e1vfvn30/prices")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "E1VFVN30",
        "prices": [
            {
                "date": "2026-08-20",
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 1000,
            },
            {
                "date": "2026-08-21",
                "open": 10.5,
                "high": 12.0,
                "low": 10.0,
                "close": 11.5,
                "volume": 1200,
            },
        ],
    }


def test_price_history_endpoint_invalid_etf(monkeypatch) -> None:
    def fake_get_etf_price_history(db_session, symbol: str, days: int | None = None):
        raise ETFNotFoundError("ETF not found: UNKNOWN")

    monkeypatch.setattr(etfs_route, "get_etf_price_history", fake_get_etf_price_history)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/etfs/UNKNOWN/prices")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "ETF not found: UNKNOWN"


def test_price_history_endpoint_passes_days_filter(monkeypatch) -> None:
    observed_days = None

    def fake_get_etf_price_history(db_session, symbol: str, days: int | None = None):
        nonlocal observed_days
        observed_days = days
        return ETFPriceHistory(symbol=symbol.upper(), prices=[])

    monkeypatch.setattr(etfs_route, "get_etf_price_history", fake_get_etf_price_history)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/etfs/E1VFVN30/prices?days=252")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert observed_days == 252


def test_price_history_endpoint_returns_chronological_order(monkeypatch) -> None:
    def fake_get_etf_price_history(db_session, symbol: str, days: int | None = None):
        return ETFPriceHistory(
            symbol=symbol.upper(),
            prices=[
                PriceHistoryPoint(date(2026, 8, 19), 9.0, 10.0, 8.0, 9.5, 900),
                PriceHistoryPoint(date(2026, 8, 20), 10.0, 11.0, 9.0, 10.5, 1000),
                PriceHistoryPoint(date(2026, 8, 21), 11.0, 12.0, 10.0, 11.5, 1100),
            ],
        )

    monkeypatch.setattr(etfs_route, "get_etf_price_history", fake_get_etf_price_history)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/etfs/E1VFVN30/prices")
    finally:
        app.dependency_overrides.clear()

    dates = [price["date"] for price in response.json()["prices"]]
    assert dates == sorted(dates)


def test_price_history_endpoint_rejects_invalid_days() -> None:
    response = TestClient(app).get("/api/etfs/E1VFVN30/prices?days=0")

    assert response.status_code == 422


def test_price_history_endpoint_rejects_too_many_days() -> None:
    response = TestClient(app).get("/api/etfs/E1VFVN30/prices?days=1501")

    assert response.status_code == 422


def test_price_history_endpoint_performs_no_database_writes(monkeypatch) -> None:
    seen_session = None

    def fake_get_etf_price_history(db_session, symbol: str, days: int | None = None):
        nonlocal seen_session
        seen_session = db_session
        return ETFPriceHistory(symbol=symbol.upper(), prices=[])

    monkeypatch.setattr(etfs_route, "get_etf_price_history", fake_get_etf_price_history)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/etfs/E1VFVN30/prices")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert isinstance(seen_session, ReadOnlyFakeSession)
