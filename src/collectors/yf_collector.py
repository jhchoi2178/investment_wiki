"""
yfinance 기반 주간(Weekly) OHLCV 데이터 수집기.
환율, 원자재 선물, 글로벌 지수 및 개별 종목 시세를 수집한다.
"""

import pandas as pd
import yfinance as yf


def fetch_weekly_ohlc(
    ticker: str,
    start_date: str,
    end_date: str | None = None,
) -> pd.DataFrame:
    """단일 티커의 주간 OHLCV 데이터를 조회하여 표준 DataFrame으로 반환한다."""
    df = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        interval="1wk",
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        return pd.DataFrame()

    # MultiIndex 컬럼 평탄화 (yfinance 최신 버전 대응)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[cols].copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["Close"])

    # yfinance 1wk 원천 데이터의 집계 시점 불일치로 인한 OHLC 역전 보정
    ohlc_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
    if len(ohlc_cols) == 4:
        df["High"] = df[ohlc_cols].max(axis=1)
        df["Low"] = df[ohlc_cols].min(axis=1)

    return df


def collect_yf_category(
    items: dict[str, dict],
    category: str,
    start_date: str,
    end_date: str | None = None,
) -> pd.DataFrame:
    """카테고리 내 yfinance 대상 모든 티커의 주간 데이터를 수집해 병합한다."""
    frames = []
    for symbol, meta in items.items():
        if meta.get("source") != "yfinance":
            continue
        df = fetch_weekly_ohlc(meta["ticker"], start_date, end_date)
        if df.empty:
            print(f"[WARN] No data for {symbol} ({meta['ticker']})")
            continue
        df["Symbol"] = symbol
        df["Name"] = meta.get("name", symbol)
        df["Category"] = category
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
