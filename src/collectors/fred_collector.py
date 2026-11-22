"""
FRED API 기반 거시경제·금리·채권·현물 원자재 데이터 수집기.
일간/월간 시계열 데이터를 주간(W-FRI) OHLC 형식으로 리샘플링하여 반환한다.
"""

import os
import pandas as pd
import requests

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred_weekly(
    series_id: str,
    start_date: str,
    end_date: str | None = None,
    api_key: str | None = None,
) -> pd.DataFrame:
    """FRED 시리즈를 조회해 주간(금요일 기준) OHLC DataFrame으로 변환한다."""
    key = api_key or os.getenv("FRED_API_KEY")
    if not key:
        raise ValueError("FRED_API_KEY 환경변수가 설정되지 않았습니다.")

    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "observation_start": start_date,
    }
    if end_date:
        params["observation_end"] = end_date

    resp = requests.get(FRED_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    observations = resp.json().get("observations", [])
    if not observations:
        return pd.DataFrame()

    df = pd.DataFrame(observations)[["date", "value"]]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    # 주간(금요일 마감) OHLC 리샘플링
    weekly = df["value"].resample("W-FRI").ohlc().dropna()
    weekly = weekly.reset_index().rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
        }
    )
    weekly["Date"] = weekly["Date"].dt.strftime("%Y-%m-%d")
    return weekly


def collect_fred_category(
    items: dict[str, dict],
    category: str,
    start_date: str,
    end_date: str | None = None,
) -> pd.DataFrame:
    """카테고리 내 FRED 대상 모든 시리즈의 주간 데이터를 수집해 병합한다."""
    frames = []
    for symbol, meta in items.items():
        if meta.get("source") != "fred":
            continue
        try:
            df = fetch_fred_weekly(meta["id"], start_date, end_date)
        except Exception as exc:
            print(f"[WARN] FRED fetch failed for {symbol} ({meta['id']}): {exc}")
            continue
        if df.empty:
            print(f"[WARN] No FRED data for {symbol} ({meta['id']})")
            continue
        df["Symbol"] = symbol
        df["Name"] = meta.get("name", symbol)
        df["Category"] = category
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
