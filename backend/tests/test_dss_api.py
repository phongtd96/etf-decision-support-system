from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.routes import dss as dss_route
from app.main import app
from app.services.dss_service import DSSDataError, SMART_CRITERIA, SmartRanking, SmartRankingItem


class ReadOnlyFakeSession:
    def add(self, value):
        raise AssertionError("DSS API must not add database rows.")

    def delete(self, value):
        raise AssertionError("DSS API must not delete database rows.")

    def commit(self):
        raise AssertionError("DSS API must not commit database changes.")

    def flush(self):
        raise AssertionError("DSS API must not flush database changes.")


def override_db() -> ReadOnlyFakeSession:
    return ReadOnlyFakeSession()


def test_dss_ranking_returns_success_response(monkeypatch) -> None:
    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_ranking)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/dss/ranking")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_dss_ranking_methodology_and_weights(monkeypatch) -> None:
    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_ranking)
    app.dependency_overrides[get_db] = override_db

    try:
        payload = TestClient(app).get("/api/dss/ranking").json()
    finally:
        app.dependency_overrides.clear()

    assert payload["methodology"] == "SMART"
    assert sum(payload["weights"].values()) == pytest.approx(1.0)
    assert payload["weights"] == {criterion.name: criterion.weight for criterion in SMART_CRITERIA}


def test_dss_rankings_are_sorted_and_ranked_from_one(monkeypatch) -> None:
    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_ranking)
    app.dependency_overrides[get_db] = override_db

    try:
        rankings = TestClient(app).get("/api/dss/ranking").json()["rankings"]
    finally:
        app.dependency_overrides.clear()

    assert [item["symbol"] for item in rankings] == ["E1VFVN30", "FUEVFVND"]
    assert [item["smart_score"] for item in rankings] == sorted(
        [item["smart_score"] for item in rankings],
        reverse=True,
    )
    assert [item["rank"] for item in rankings] == [1, 2]


def test_dss_criterion_details_are_complete_and_valid(monkeypatch) -> None:
    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_ranking)
    app.dependency_overrides[get_db] = override_db

    try:
        item = TestClient(app).get("/api/dss/ranking").json()["rankings"][0]
    finally:
        app.dependency_overrides.clear()

    assert set(item["criteria"]) == {criterion.name for criterion in SMART_CRITERIA}
    for criterion in SMART_CRITERIA:
        detail = item["criteria"][criterion.name]
        assert set(detail) == {
            "raw_value",
            "utility",
            "weight",
            "weighted_contribution",
            "criterion_type",
        }
        assert 0 <= detail["utility"] <= 1
        assert detail["weight"] == criterion.weight
        assert detail["criterion_type"] == criterion.criterion_type.value


def test_dss_weighted_contributions_sum_to_score(monkeypatch) -> None:
    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_ranking)
    app.dependency_overrides[get_db] = override_db

    try:
        rankings = TestClient(app).get("/api/dss/ranking").json()["rankings"]
    finally:
        app.dependency_overrides.clear()

    for item in rankings:
        total_contribution = sum(
            detail["weighted_contribution"] for detail in item["criteria"].values()
        )
        assert total_contribution == pytest.approx(item["smart_score"])


def test_dss_detail_returns_requested_etf_and_matching_score(monkeypatch) -> None:
    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_ranking)
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        ranking_item = client.get("/api/dss/ranking").json()["rankings"][1]
        detail_item = client.get("/api/dss/fuevfvnd").json()
    finally:
        app.dependency_overrides.clear()

    assert detail_item["symbol"] == "FUEVFVND"
    assert detail_item["smart_score"] == ranking_item["smart_score"]
    assert detail_item["rank"] == ranking_item["rank"]


def test_dss_invalid_symbol_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_ranking)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/dss/UNKNOWN")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "UNKNOWN" in response.json()["detail"]


def test_dss_ranking_route_is_not_captured_by_symbol_route(monkeypatch) -> None:
    calls = {"ranking": 0}

    def fake_service(db_session):
        calls["ranking"] += 1
        return fake_ranking(db_session)

    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_service)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/dss/ranking")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == {"ranking": 1}
    assert response.json()["rankings"][0]["symbol"] == "E1VFVN30"


def test_dss_all_missing_data_returns_404(monkeypatch) -> None:
    def fake_service(db_session):
        raise DSSDataError("No ETF alternatives available for SMART ranking.")

    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_service)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/dss/ranking")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "No ETF alternatives available for SMART ranking."


def test_dss_api_performs_no_database_writes(monkeypatch) -> None:
    seen_session = None

    def fake_service(db_session):
        nonlocal seen_session
        seen_session = db_session
        return fake_ranking(db_session)

    monkeypatch.setattr(dss_route, "calculate_smart_ranking_from_database", fake_service)
    app.dependency_overrides[get_db] = override_db

    try:
        response = TestClient(app).get("/api/dss/ranking")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert isinstance(seen_session, ReadOnlyFakeSession)


def test_existing_health_api_does_not_regress() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def fake_ranking(db_session) -> SmartRanking:
    return SmartRanking(
        as_of_date=date(2026, 8, 21),
        rankings=[
            SmartRankingItem(
                rank=1,
                symbol="E1VFVN30",
                date=date(2026, 8, 21),
                raw_values={
                    "technical_momentum": 82.0,
                    "return_20d": 0.04,
                    "volatility_20d": 0.12,
                    "max_drawdown_60d": 0.05,
                    "avg_volume_20d": 1_500_000.0,
                },
                utilities={
                    "technical_momentum": 1.0,
                    "return_20d": 0.8,
                    "volatility_20d": 0.7,
                    "max_drawdown_60d": 0.5,
                    "avg_volume_20d": 0.635,
                },
                weighted_contributions={
                    "technical_momentum": 30.0,
                    "return_20d": 20.0,
                    "volatility_20d": 14.0,
                    "max_drawdown_60d": 7.5,
                    "avg_volume_20d": 6.35,
                },
                smart_score=77.85,
                reasons=["Strong technical momentum relative to other ETFs."],
            ),
            SmartRankingItem(
                rank=2,
                symbol="FUEVFVND",
                date=date(2026, 8, 21),
                raw_values={
                    "technical_momentum": 65.0,
                    "return_20d": 0.02,
                    "volatility_20d": 0.10,
                    "max_drawdown_60d": 0.04,
                    "avg_volume_20d": 900_000.0,
                },
                utilities={
                    "technical_momentum": 0.5,
                    "return_20d": 0.6,
                    "volatility_20d": 0.8,
                    "max_drawdown_60d": 0.6,
                    "avg_volume_20d": 0.5,
                },
                weighted_contributions={
                    "technical_momentum": 15.0,
                    "return_20d": 15.0,
                    "volatility_20d": 16.0,
                    "max_drawdown_60d": 9.0,
                    "avg_volume_20d": 5.0,
                },
                smart_score=60.0,
                reasons=["Balanced SMART profile across the selected criteria."],
            ),
        ],
    )
