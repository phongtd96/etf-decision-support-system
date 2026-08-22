from datetime import date

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app
from app.services.analysis_service import (
    LatestTechnicalAnalysis,
    TechnicalAnalysisNotFoundError,
    TechnicalRanking,
    TechnicalRankingItem,
    TechnicalSignal,
)
from app.api.routes import analysis as analysis_route


def override_db() -> None:
    return None


def test_analysis_api_success_response(monkeypatch) -> None:
    def fake_get_latest_technical_analysis(db_session, symbol: str):
        return LatestTechnicalAnalysis(
            symbol=symbol,
            date=date(2026, 8, 21),
            technical_score=85.0,
            technical_signal=TechnicalSignal.BULLISH,
            indicators={
                "sma_20": 20.0,
                "sma_50": 18.0,
                "rsi_14": 60.0,
                "macd": 1.2,
                "macd_signal": 0.8,
                "volatility_20": 0.18,
            },
            reasons=["Trend is bullish because SMA20 is above SMA50."],
        )

    monkeypatch.setattr(
        analysis_route,
        "get_latest_technical_analysis",
        fake_get_latest_technical_analysis,
    )
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get("/api/analysis/e1vfvn30")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "E1VFVN30",
        "date": "2026-08-21",
        "technical_score": 85.0,
        "technical_signal": "BULLISH",
        "indicators": {
            "sma_20": 20.0,
            "sma_50": 18.0,
            "rsi_14": 60.0,
            "macd": 1.2,
            "macd_signal": 0.8,
            "volatility_20": 0.18,
        },
        "reasons": ["Trend is bullish because SMA20 is above SMA50."],
    }


def test_analysis_api_404_behavior(monkeypatch) -> None:
    def fake_get_latest_technical_analysis(db_session, symbol: str):
        raise TechnicalAnalysisNotFoundError("No technical indicator data found")

    monkeypatch.setattr(
        analysis_route,
        "get_latest_technical_analysis",
        fake_get_latest_technical_analysis,
    )
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get("/api/analysis/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "No technical indicator data found"


def test_analysis_ranking_api_success_response(monkeypatch) -> None:
    def fake_get_technical_ranking(db_session):
        return TechnicalRanking(
            as_of_date=date(2026, 8, 21),
            rankings=[
                TechnicalRankingItem(
                    rank=1,
                    symbol="E1VFVN30",
                    date=date(2026, 8, 21),
                    technical_score=80.0,
                    technical_signal=TechnicalSignal.BULLISH,
                ),
                TechnicalRankingItem(
                    rank=2,
                    symbol="FUEVFVND",
                    date=date(2026, 8, 20),
                    technical_score=70.0,
                    technical_signal=TechnicalSignal.NEUTRAL,
                ),
            ],
        )

    monkeypatch.setattr(
        analysis_route,
        "get_technical_ranking",
        fake_get_technical_ranking,
    )
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get("/api/analysis/ranking")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "as_of_date": "2026-08-21",
        "rankings": [
            {
                "rank": 1,
                "symbol": "E1VFVN30",
                "date": "2026-08-21",
                "technical_score": 80.0,
                "technical_signal": "BULLISH",
            },
            {
                "rank": 2,
                "symbol": "FUEVFVND",
                "date": "2026-08-20",
                "technical_score": 70.0,
                "technical_signal": "NEUTRAL",
            },
        ],
    }


def test_analysis_ranking_route_is_not_captured_by_symbol_route(monkeypatch) -> None:
    calls = {"ranking": 0, "symbol": 0}

    def fake_get_technical_ranking(db_session):
        calls["ranking"] += 1
        return TechnicalRanking(as_of_date=date(2026, 8, 21), rankings=[])

    def fake_get_latest_technical_analysis(db_session, symbol: str):
        calls["symbol"] += 1
        raise AssertionError("Dynamic symbol route should not handle /ranking")

    monkeypatch.setattr(
        analysis_route,
        "get_technical_ranking",
        fake_get_technical_ranking,
    )
    monkeypatch.setattr(
        analysis_route,
        "get_latest_technical_analysis",
        fake_get_latest_technical_analysis,
    )
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get("/api/analysis/ranking")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == {"ranking": 1, "symbol": 0}


def test_analysis_ranking_api_404_behavior(monkeypatch) -> None:
    def fake_get_technical_ranking(db_session):
        raise TechnicalAnalysisNotFoundError("No technical analysis data available.")

    monkeypatch.setattr(
        analysis_route,
        "get_technical_ranking",
        fake_get_technical_ranking,
    )
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get("/api/analysis/ranking")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "No technical analysis data available."
