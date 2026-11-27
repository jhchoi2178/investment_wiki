"""
한국은행 ECOS Open API 기반 한국 국고채 및 기준금리 데이터 수집기.
일간 시계열 데이터를 주간(W-FRI) OHLC 형식으로 리샘플링하여 반환한다.
"""

import os
from datetime import datetime
import pandas as pd
import requests

ECOS_BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"


def fetch_ecos_weekly(
    stat_code: str,
    item_code: str,
    start_date: str,
    end_date: str | None = None,
    api_key: str | None = None,
) -> pd.DataFrame:
    """ECOS 통계코드를 조회해 주간(금요일 기준) OHLC DataFrame으로 변환한다."""
    key = api_key or os.getenv("ECOS_API_KEY")
    if not key:
        raise ValueError("ECOS_API_KEY 환경변수가 설정되지 않았습니다.")

    start_fmt = start_date.replace("-", "")
    end_fmt = (end_date or datetime.today().strftime("%Y-%m-%d")).replace("-", "")
    url = f"{ECOS_BASE_URL}/{key}/json/kr/1/10000/{stat_code}/D/{start_fmt}/{end_fmt}/{item_code}"

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    rows = resp.json().get("StatisticSearch", {}).get("row", [])
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]]
    df["value"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
    df = df.dropna(subset=["value"])
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["TIME"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")

    # 일간 OHLC 형식 변환 (단일 종가 기준 O=H=L=C)
    daily = pd.DataFrame({
        "Date": df["date"].dt.strftime("%Y-%m-%d"),
        "Open": df["value"],
        "High": df["value"],
        "Low": df["value"],
        "Close": df["value"],
    })
    return daily


def collect_ecos_category(
    items: dict[str, dict],
    category: str,
    start_date: str,
    end_date: str | None = None,
) -> pd.DataFrame:
    """카테고리 내 ECOS 대상 모든 지표의 주간 데이터를 수집해 병합한다."""
    frames = []
    for symbol, meta in items.items():
        if meta.get("source") != "ecos":
            continue
        try:
            df = fetch_ecos_weekly(meta["stat_code"], meta["item_code"], start_date, end_date)
        except Exception as exc:
            print(f"[WARN] ECOS fetch failed for {symbol}: {exc}")
            continue
        if df.empty:
            print(f"[WARN] No ECOS data for {symbol}")
            continue
        df["Symbol"] = symbol
        df["Name"] = meta.get("name", symbol)
        df["Category"] = category
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
