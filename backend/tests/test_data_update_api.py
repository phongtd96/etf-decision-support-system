from datetime import date

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.routes import data as data_route
from app.main import app
from app.services.market_data_update_service import (
    MarketDataUpdateError,
    MarketDataUpdateSummary,
    SymbolUpdateSummary,
)
from app.api.routes.data import PUBLIC_UPDATE_FAILURE_MESSAGE


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def override_db() -> FakeSession:
    return FakeSession()


def test_data_update_success_with_new_market_data(monkeypatch) -> None:
    seen_session = None

    def fake_update_market_data(db_session):
        nonlocal seen_session
        seen_session = db_session
        return MarketDataUpdateSummary(
            status="updated",
            latest_date=date(2026, 8, 24),
            processed_price_rows=3,
            symbols_updated=["E1VFVN30"],
            indicators_recalculated=True,
            message="Market data update completed successfully.",
            details=[
                SymbolUpdateSummary(
                    symbol="E1VFVN30",
                    fetched_rows=4,
                    valid_rows=4,
                    changed_rows=3,
                    latest_date=date(2026, 8, 24),
                    indicators_recalculated=True,
                    indicator_rows=1200,
                    status="updated",
                    message="Price data changed; technical indicators recalculated.",
                )
            ],
        )

    monkeypatch.setattr(data_route, "update_market_data", fake_update_market_data)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).post("/api/data/update")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    assert response.json()["processed_price_rows"] == 3
    assert response.json()["symbols_updated"] == ["E1VFVN30"]
    assert response.json()["indicators_recalculated"] is True
    assert isinstance(seen_session, FakeSession)
    assert seen_session.commits == 1
    assert seen_session.rollbacks == 0


def test_data_update_already_current(monkeypatch) -> None:
    def fake_update_market_data(db_session):
        return MarketDataUpdateSummary(
            status="already_up_to_date",
            latest_date=date(2026, 8, 24),
            processed_price_rows=0,
            symbols_updated=[],
            indicators_recalculated=False,
            message="Data is already up to date.",
            details=[
                SymbolUpdateSummary(
                    symbol="E1VFVN30",
                    fetched_rows=1,
                    valid_rows=1,
                    changed_rows=0,
                    latest_date=date(2026, 8, 24),
                    indicators_recalculated=False,
                    indicator_rows=0,
                    status="already_up_to_date",
                    message="No new or changed price records.",
                )
            ],
        )

    monkeypatch.setattr(data_route, "update_market_data", fake_update_market_data)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).post("/api/data/update")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "already_up_to_date"
    assert response.json()["processed_price_rows"] == 0
    assert response.json()["message"] == "Data is already up to date."


def test_data_update_external_failure_returns_controlled_error(monkeypatch) -> None:
    seen_session = None

    def fake_update_market_data(db_session):
        nonlocal seen_session
        seen_session = db_session
        raise MarketDataUpdateError("VCI provider unavailable")

    monkeypatch.setattr(data_route, "update_market_data", fake_update_market_data)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).post("/api/data/update")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "VCI provider unavailable"
    assert isinstance(seen_session, FakeSession)
    assert seen_session.commits == 0
    assert seen_session.rollbacks == 1


def test_data_update_unexpected_failure_returns_safe_public_message(monkeypatch) -> None:
    raw_exception_text = "database password leaked in raw exception"

    def fake_update_market_data(db_session):
        raise RuntimeError(raw_exception_text)

    monkeypatch.setattr(data_route, "update_market_data", fake_update_market_data)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).post("/api/data/update")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == PUBLIC_UPDATE_FAILURE_MESSAGE
    assert raw_exception_text not in response.text


def test_health_endpoint_still_behaves() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
