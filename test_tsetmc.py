import tse_option as tso

print("====================================")
print("TSE OPTION REAL DATA TEST")
print("====================================")

try:
    df = tso.option_chain(
        symbol="خودرو",
        trading_days=100,
        IV=False,
        leverage=True,
        P_BSM=False,
        sort="Maturity"
    )

    print("SUCCESS")
    print("ROWS:", len(df))
    print("COLUMNS:")
    print(list(df.columns))

    print("\nFIRST 10 ROWS:")
    print(df.head(10).to_string())

except Exception as e:
    print("FAILED")
    print("ERROR:", repr(e))