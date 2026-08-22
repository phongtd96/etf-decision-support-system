from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
from vnstock import Quote


PRIMARY_SOURCE = "kbs"
SECONDARY_SOURCE_CANDIDATES = ["vci", "msn"]
INTERVAL = "1D"
WINDOW_DAYS = 7
COMPARE_COLUMNS = ["open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class Anomaly:
    symbol: str
    date: str


ANOMALIES = [
    Anomaly(symbol="FUEVFVND", date="2025-05-06"),
    Anomaly(symbol="FUEDCMID", date="2025-06-04"),
    Anomaly(symbol="FUESSVFL", date="2025-05-08"),
]


def fetch_history(source: str, symbol: str, start: str, end: str) -> pd.DataFrame:
    quote = Quote(source=source, symbol=symbol)
    return quote.history(start=start, end=end, interval=INTERVAL)


def normalize_history(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    required_columns = ["time", *COMPARE_COLUMNS]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    normalized = df[required_columns].copy()
    normalized["date"] = pd.to_datetime(normalized["time"], errors="coerce").dt.date
    normalized = normalized.drop(columns=["time"])

    for column in COMPARE_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    start_date = pd.Timestamp(start).date()
    end_date = pd.Timestamp(end).date()
    normalized = normalized.loc[
        normalized["date"].between(start_date, end_date, inclusive="both")
    ]

    normalized = normalized.sort_values("date").reset_index(drop=True)
    return normalized[["date", *COMPARE_COLUMNS]]


def first_available_secondary_source(
    symbol: str,
    start: str,
    end: str,
) -> tuple[str | None, pd.DataFrame | None, list[str]]:
    errors: list[str] = []

    for source in SECONDARY_SOURCE_CANDIDATES:
        try:
            df = normalize_history(fetch_history(source, symbol, start, end), start, end)
        except Exception as exc:
            errors.append(f"{source}: {exc}")
            continue

        if df.empty:
            errors.append(f"{source}: returned an empty dataset")
            continue

        return source, df, errors

    return None, None, errors


def format_decimal(value: Any) -> str:
    if pd.isna(value):
        return "NA"

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)

    return format(decimal_value.normalize(), "f")


def values_differ(left: Any, right: Any) -> bool:
    if pd.isna(left) and pd.isna(right):
        return False
    if pd.isna(left) or pd.isna(right):
        return True
    return Decimal(str(left)) != Decimal(str(right))


def build_comparison(primary_df: pd.DataFrame, secondary_df: pd.DataFrame) -> pd.DataFrame:
    comparison = primary_df.merge(
        secondary_df,
        on="date",
        how="outer",
        suffixes=(f"_{PRIMARY_SOURCE}", "_secondary"),
        indicator=True,
    )
    comparison = comparison.sort_values("date").reset_index(drop=True)
    return comparison


def print_source_rows(source: str, df: pd.DataFrame) -> None:
    printable = df.copy()
    for column in COMPARE_COLUMNS:
        printable[column] = printable[column].map(format_decimal)
    print(f"\n{source} surrounding rows:")
    print(printable.to_string(index=False))


def print_differences(comparison: pd.DataFrame, secondary_source: str) -> None:
    difference_rows: list[dict[str, Any]] = []

    for _, row in comparison.iterrows():
        if row["_merge"] != "both":
            difference_rows.append(
                {
                    "date": row["date"],
                    "field": "row_presence",
                    PRIMARY_SOURCE: "present" if row["_merge"] != "right_only" else "missing",
                    secondary_source: "present" if row["_merge"] != "left_only" else "missing",
                }
            )
            continue

        for column in COMPARE_COLUMNS:
            primary_value = row[f"{column}_{PRIMARY_SOURCE}"]
            secondary_value = row[f"{column}_secondary"]
            if values_differ(primary_value, secondary_value):
                difference_rows.append(
                    {
                        "date": row["date"],
                        "field": column,
                        PRIMARY_SOURCE: format_decimal(primary_value),
                        secondary_source: format_decimal(secondary_value),
                    }
                )

    if not difference_rows:
        print("\nDifferences between sources: none on overlapping rows")
        return

    print("\nDifferences between sources:")
    print(pd.DataFrame(difference_rows).to_string(index=False))


def print_anomaly_day_comparison(
    comparison: pd.DataFrame,
    anomaly_date: str,
    secondary_source: str,
) -> None:
    target_date = pd.Timestamp(anomaly_date).date()
    target_rows = comparison.loc[comparison["date"] == target_date]

    print(f"\nAnomaly date comparison: {anomaly_date}")
    if target_rows.empty:
        print("No row found for the anomaly date in either source.")
        return

    row = target_rows.iloc[0]
    if row["_merge"] != "both":
        print(f"Row availability: {row['_merge']}")
        return

    rows = []
    for column in COMPARE_COLUMNS:
        primary_value = row[f"{column}_{PRIMARY_SOURCE}"]
        secondary_value = row[f"{column}_secondary"]
        rows.append(
            {
                "field": column,
                PRIMARY_SOURCE: format_decimal(primary_value),
                secondary_source: format_decimal(secondary_value),
                "match": not values_differ(primary_value, secondary_value),
            }
        )

    table = pd.DataFrame(rows).rename(columns={secondary_source: secondary_source})
    print(table.to_string(index=False))


def print_investigation(anomaly: Anomaly) -> None:
    anomaly_date = pd.Timestamp(anomaly.date).date()
    start = (anomaly_date - timedelta(days=WINDOW_DAYS)).isoformat()
    end = (anomaly_date + timedelta(days=WINDOW_DAYS)).isoformat()

    print(f"\n{'=' * 88}")
    print(f"Symbol: {anomaly.symbol}")
    print(f"Anomaly date: {anomaly.date}")
    print(f"Window: {start} to {end}")
    print(f"Primary source: {PRIMARY_SOURCE}")

    try:
        primary_df = normalize_history(
            fetch_history(PRIMARY_SOURCE, anomaly.symbol, start, end),
            start,
            end,
        )
    except Exception as exc:
        print(f"Primary source error: {exc}")
        return

    print_source_rows(PRIMARY_SOURCE, primary_df)

    secondary_source, secondary_df, errors = first_available_secondary_source(
        anomaly.symbol,
        start,
        end,
    )

    if secondary_source is None or secondary_df is None:
        print("\nSecond source unavailable.")
        for error in errors:
            print(f"- {error}")
        return

    print(f"\nSecond source used: {secondary_source}")
    if errors:
        print("Earlier second-source attempts:")
        for error in errors:
            print(f"- {error}")

    print_source_rows(secondary_source, secondary_df)

    comparison = build_comparison(primary_df, secondary_df)
    print_anomaly_day_comparison(comparison, anomaly.date, secondary_source)
    print_differences(comparison, secondary_source)


def main() -> None:
    print("Cross-source OHLC anomaly investigation")
    print("This script reports differences only. It does not modify or correct data.")
    print(f"Secondary sources tried in order: {', '.join(SECONDARY_SOURCE_CANDIDATES)}")

    for anomaly in ANOMALIES:
        print_investigation(anomaly)


if __name__ == "__main__":
    main()
