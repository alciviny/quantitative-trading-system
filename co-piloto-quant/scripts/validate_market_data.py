import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "../src/co_piloto_quant/data/raw/market_data.db"
DB_PATH = DB_PATH.resolve()

REQUIRED_COLS = ["date", "open", "high", "low", "close", "volume"]


def validate_ohlcv_integrity(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    tickers = [row[0] for row in conn.execute("SELECT DISTINCT ticker FROM ohlcv")]
    report = []
    for ticker in tickers:
        df = pd.read_sql_query("SELECT * FROM ohlcv WHERE ticker = ? ORDER BY date", conn, params=(ticker,))
        n_rows = len(df)
        missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
        if not missing_cols:
            nulls = df[REQUIRED_COLS].isnull().sum().to_dict()
        else:
            nulls = dict.fromkeys(missing_cols, 'MISSING')
        date_gaps = None
        if "date" in df.columns and n_rows > 1:
            dates = pd.to_datetime(df["date"])
            gaps = (dates - dates.shift(1)).dt.days.fillna(0)
            max_gap = gaps.max()
            date_gaps = int(max_gap) if max_gap > 1 else 0
        else:
            date_gaps = 'MISSING'
        report.append({
            "ticker": ticker,
            "rows": n_rows,
            "nulls": nulls,
            "max_date_gap": date_gaps
        })
    conn.close()
    return report

if __name__ == "__main__":
    report = validate_ohlcv_integrity()
    print("Ticker | Linhas | Nulos por coluna | Maior gap de datas")
    for r in report:
        print(f"{r['ticker']} | {r['rows']} | {r['nulls']} | {r['max_date_gap']}")
    print("\nValidação concluída.")
