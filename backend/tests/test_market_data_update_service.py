from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from app.services import market_data_update_service as service
from app.services.market_data_update_service import update_market_data, update_symbol_market_data


def provider_frame(close: float = 11.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": ["2026-08-24"],
            "open": [10.0],
            "high": [12.0],
            "low": [9.0],
            "close": [close],
            "volume": [1000],
        }
    )


class FakeSession:
    def scalar(self, statement):
        return SimpleNamespace(id=1, symbol="E1VFVN30")


def test_update_symbol_recalculates_indicators_when_price_data_changes(monkeypatch) -> None:
    calls = {"save_price": 0, "save_indicators": 0}

    monkeypatch.setattr(
        service,
        "get_symbol_fetch_start_date",
        lambda db_session, etf, start_date: date(2026, 8, 23),
    )
    monkeypatch.setattr(service, "fetch_etf_history", lambda **kwargs: provider_frame())
    monkeypatch.setattr(
        service,
        "filter_changed_price_rows",
        lambda db_session, etf, df: df,
    )

    def fake_save_price_history(db_session, etf, df, data_source):
        calls["save_price"] += 1
        return SimpleNamespace(processed_rows=len(df))

    def fake_save_technical_indicators(db_session, etf, indicators_df):
        calls["save_indicators"] += 1
        return SimpleNamespace(processed_rows=len(indicators_df))

    monkeypatch.setattr(service, "save_price_history", fake_save_price_history)
    monkeypatch.setattr(
        service,
        "load_price_history",
        lambda db_session, symbol: pd.DataFrame(
            {"date": [date(2026, 8, 24)], "close": [11.0]}
        ),
    )
    monkeypatch.setattr(
        service,
        "calculate_technical_indicators",
        lambda price_df: pd.DataFrame({"date": price_df["date"], "sma_20": [None]}),
    )
    monkeypatch.setattr(service, "save_technical_indicators", fake_save_technical_indicators)

    summary = update_symbol_market_data(FakeSession(), "E1VFVN30")

    assert summary.changed_rows == 1
    assert summary.indicators_recalculated is True
    assert calls == {"save_price": 1, "save_indicators": 1}


def test_update_symbol_does_not_upsert_duplicate_unchanged_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "get_symbol_fetch_start_date",
        lambda db_session, etf, start_date: date(2026, 8, 24),
    )
    monkeypatch.setattr(service, "fetch_etf_history", lambda **kwargs: provider_frame())
    monkeypatch.setattr(
        service,
        "filter_changed_price_rows",
        lambda db_session, etf, df: df.iloc[0:0].copy(),
    )

    def fail_save_price_history(db_session, etf, df, data_source):
        raise AssertionError("Unchanged rows must not be upserted.")

    def fail_save_technical_indicators(db_session, etf, indicators_df):
        raise AssertionError("Indicators must not recalculate when price data is unchanged.")

    monkeypatch.setattr(service, "save_price_history", fail_save_price_history)
    monkeypatch.setattr(service, "save_technical_indicators", fail_save_technical_indicators)

    summary = update_symbol_market_data(FakeSession(), "E1VFVN30")

    assert summary.changed_rows == 0
    assert summary.status == "already_up_to_date"
    assert summary.indicators_recalculated is False


def test_update_symbol_propagates_external_data_source_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "get_symbol_fetch_start_date",
        lambda db_session, etf, start_date: date(2026, 8, 24),
    )

    def fail_fetch(**kwargs):
        raise RuntimeError("provider timeout")

    monkeypatch.setattr(service, "fetch_etf_history", fail_fetch)

    with pytest.raises(RuntimeError, match="provider timeout"):
        update_symbol_market_data(FakeSession(), "E1VFVN30")


def test_update_market_data_empty_provider_uses_existing_db_latest_date(monkeypatch) -> None:
    latest_db_date = date(2026, 8, 21)

    monkeypatch.setattr(
        service,
        "get_latest_stored_price_date",
        lambda db_session: latest_db_date,
    )
    monkeypatch.setattr(
        service,
        "update_symbol_market_data",
        lambda db_session, symbol, start_date: service.SymbolUpdateSummary(
            symbol=symbol,
            fetched_rows=0,
            valid_rows=0,
            changed_rows=0,
            latest_date=None,
            indicators_recalculated=False,
            indicator_rows=0,
            status="already_up_to_date",
            message="No newer price records returned by data source.",
        ),
    )

    summary = update_market_data(object(), symbols=["E1VFVN30"])

    assert summary.status == "already_up_to_date"
    assert summary.latest_date == latest_db_date
    assert summary.processed_price_rows == 0


def test_update_market_data_empty_provider_and_empty_db_has_null_latest_date(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        service,
        "get_latest_stored_price_date",
        lambda db_session: None,
    )
    monkeypatch.setattr(
        service,
        "update_symbol_market_data",
        lambda db_session, symbol, start_date: service.SymbolUpdateSummary(
            symbol=symbol,
            fetched_rows=0,
            valid_rows=0,
            changed_rows=0,
            latest_date=None,
            indicators_recalculated=False,
            indicator_rows=0,
            status="already_up_to_date",
            message="No newer price records returned by data source.",
        ),
    )

    summary = update_market_data(object(), symbols=["E1VFVN30"])

    assert summary.status == "already_up_to_date"
    assert summary.latest_date is None
    assert summary.processed_price_rows == 0
