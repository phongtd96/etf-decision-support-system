from datetime import date

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app
from app.services.analysis_service import (
    LatestTechnicalAnalysis,
    TechnicalAnalysisNotFoundError,
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
