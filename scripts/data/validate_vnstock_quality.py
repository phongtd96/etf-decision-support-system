from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from vnstock import Quote


SYMBOLS = [
    "E1VFVN30",
    "FUEVFVND",
    "FUEVN100",
    "FUEDCMID",
    "FUESSVFL",
]

START_DATE = "2022-01-01"
END_DATE = "2026-08-22"
INTERVAL = "1D"
REQUIRED_COLUMNS = ["time", "open", "high", "low", "close", "volume"]
OHLC_COLUMNS = ["open", "high", "low", "close"]
QUALITY_COLUMNS = ["open", "high", "low", "close", "volume"]


@dataclass
class ValidationSummary:
    symbol: str
    row_count: int
    min_date: str | None
    max_date: str | None
    missing_counts: dict[str, int]
    duplicate_date_count: int
    invalid_ohlc_count: int
    invalid_volume_count: int
    non_monotonic_date_count: int
    duplicate_row_count: int
    empty_dataset: bool
    error: str | None = None


def download_history(symbol: str) -> pd.DataFrame:
    quote = Quote(symbol=symbol)
    return quote.history(start=START_DATE, end=END_DATE, interval=INTERVAL)


def validate_dataframe(symbol: str, df: pd.DataFrame) -> tuple[ValidationSummary, dict[str, pd.DataFrame]]:
    issues: dict[str, pd.DataFrame] = {}
    empty_dataset = df.empty

    missing_required_columns = [
        column for column in REQUIRED_COLUMNS if column not in df.columns
    ]
    if missing_required_columns:
        summary = ValidationSummary(
            symbol=symbol,
            row_count=len(df),
            min_date=None,
            max_date=None,
            missing_counts={column: 0 for column in QUALITY_COLUMNS},
            duplicate_date_count=0,
            invalid_ohlc_count=0,
            invalid_volume_count=0,
            non_monotonic_date_count=0,
            duplicate_row_count=0,
            empty_dataset=empty_dataset,
            error=f"Missing required columns: {missing_required_columns}",
        )
        return summary, issues

    original_df = df.copy()
    working_df = df.copy()
    working_df["time"] = pd.to_datetime(working_df["time"], errors="coerce")

    for column in QUALITY_COLUMNS:
        working_df[column] = pd.to_numeric(working_df[column], errors="coerce")

    missing_counts = {
        column: int(original_df[column].isna().sum()) for column in QUALITY_COLUMNS
    }

    duplicate_date_mask = working_df["time"].duplicated(keep=False)
    duplicate_date_count = int(working_df["time"].duplicated().sum())
    if duplicate_date_mask.any():
        issues["duplicate_dates"] = working_df.loc[duplicate_date_mask]

    non_numeric_ohlc_mask = pd.Series(False, index=working_df.index)
    for column in OHLC_COLUMNS:
        non_numeric_ohlc_mask = non_numeric_ohlc_mask | (
            original_df[column].notna() & working_df[column].isna()
        )

    invalid_ohlc_mask = (
        (working_df["high"] < working_df["low"])
        | (working_df["open"] > working_df["high"])
        | (working_df["open"] < working_df["low"])
        | (working_df["close"] > working_df["high"])
        | (working_df["close"] < working_df["low"])
        | non_numeric_ohlc_mask
    )
    invalid_ohlc_count = int(invalid_ohlc_mask.sum())
    if invalid_ohlc_mask.any():
        issues["invalid_ohlc"] = working_df.loc[invalid_ohlc_mask]

    invalid_volume_mask = (
        (original_df["volume"].notna() & working_df["volume"].isna())
        | working_df["volume"].lt(0)
    )
    invalid_volume_count = int(invalid_volume_mask.sum())
    if invalid_volume_mask.any():
        issues["invalid_volume"] = working_df.loc[invalid_volume_mask]

    non_monotonic_date_mask = working_df["time"].diff().dt.days.lt(0)
    non_monotonic_date_count = int(non_monotonic_date_mask.sum())
    if non_monotonic_date_mask.any():
        issues["non_monotonic_dates"] = working_df.loc[non_monotonic_date_mask]

    duplicate_row_mask = working_df.duplicated(keep=False)
    duplicate_row_count = int(working_df.duplicated().sum())
    if duplicate_row_mask.any():
        issues["duplicate_rows"] = working_df.loc[duplicate_row_mask]

    valid_dates = working_df["time"].dropna()
    summary = ValidationSummary(
        symbol=symbol,
        row_count=len(working_df),
        min_date=format_date(valid_dates.min()) if not valid_dates.empty else None,
        max_date=format_date(valid_dates.max()) if not valid_dates.empty else None,
        missing_counts=missing_counts,
        duplicate_date_count=duplicate_date_count,
        invalid_ohlc_count=invalid_ohlc_count,
        invalid_volume_count=invalid_volume_count,
        non_monotonic_date_count=non_monotonic_date_count,
        duplicate_row_count=duplicate_row_count,
        empty_dataset=empty_dataset,
    )
    return summary, issues


def format_date(value: Any) -> str:
    return pd.Timestamp(value).date().isoformat()


def print_summary(summary: ValidationSummary, issues: dict[str, pd.DataFrame]) -> None:
    print(f"\n{'=' * 72}")
    print(f"Symbol: {summary.symbol}")
    print(f"Rows: {summary.row_count}")
    print(f"Minimum date: {summary.min_date}")
    print(f"Maximum date: {summary.max_date}")
    print(f"Empty dataset: {summary.empty_dataset}")

    if summary.error:
        print(f"Error: {summary.error}")
        return

    print("Missing values:")
    for column, count in summary.missing_counts.items():
        print(f"  {column}: {count}")

    print(f"Duplicate date count: {summary.duplicate_date_count}")
    print(f"Invalid OHLC row count: {summary.invalid_ohlc_count}")
    print(f"Invalid volume row count: {summary.invalid_volume_count}")
    print(f"Non-monotonic date count: {summary.non_monotonic_date_count}")
    print(f"Duplicate row count: {summary.duplicate_row_count}")

    if not issues:
        print("Issues: none")
        return

    print("Issues found:")
    for issue_name, issue_df in issues.items():
        print(f"\n{issue_name}:")
        print(issue_df.to_string(index=False))


def main() -> None:
    summaries: list[ValidationSummary] = []

    print("Vietnamese ETF data quality validation")
    print(f"Source: vnstock Quote.history()")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Interval: {INTERVAL}")

    for symbol in SYMBOLS:
        try:
            df = download_history(symbol)
            summary, issues = validate_dataframe(symbol, df)
        except Exception as exc:
            summary = ValidationSummary(
                symbol=symbol,
                row_count=0,
                min_date=None,
                max_date=None,
                missing_counts={column: 0 for column in QUALITY_COLUMNS},
                duplicate_date_count=0,
                invalid_ohlc_count=0,
                invalid_volume_count=0,
                non_monotonic_date_count=0,
                duplicate_row_count=0,
                empty_dataset=True,
                error=str(exc),
            )
            issues = {}

        summaries.append(summary)
        print_summary(summary, issues)

    print(f"\n{'=' * 72}")
    print("Validation summary table")
    summary_table = pd.DataFrame(
        {
            "symbol": summary.symbol,
            "row_count": summary.row_count,
            "min_date": summary.min_date,
            "max_date": summary.max_date,
            "missing_open": summary.missing_counts["open"],
            "missing_high": summary.missing_counts["high"],
            "missing_low": summary.missing_counts["low"],
            "missing_close": summary.missing_counts["close"],
            "missing_volume": summary.missing_counts["volume"],
            "duplicate_dates": summary.duplicate_date_count,
            "invalid_ohlc": summary.invalid_ohlc_count,
            "invalid_volume": summary.invalid_volume_count,
            "non_monotonic_dates": summary.non_monotonic_date_count,
            "duplicate_rows": summary.duplicate_row_count,
            "error": summary.error,
        }
        for summary in summaries
    )
    print(summary_table.to_string(index=False))


if __name__ == "__main__":
    main()
