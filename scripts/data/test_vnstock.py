from vnstock import Quote

symbols = [
    "E1VFVN30",
    "FUEVFVND",
    "FUEVN100",
    "FUEDCMID",
    "FUESSVFL",
]

for symbol in symbols:
    print(f"\n{'=' * 60}")
    print(f"Testing: {symbol}")

    try:
        quote = Quote(symbol=symbol)

        df = quote.history(
            start="2022-01-01",
            end="2026-08-22",
            interval="1D",
        )

        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")

        if not df.empty:
            print(df.head(3))
            print(df.tail(3))

    except Exception as exc:
        print(f"ERROR: {exc}")