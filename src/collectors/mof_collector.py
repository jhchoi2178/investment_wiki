"""
일본 재무성(MOF) 공식 일별 국채 금리 CSV를 수집하여 주간(Weekly) OHLC로 변환한다.
"""

import io
import pandas as pd
import requests

MOF_HIST_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
MOF_CURR_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"


def _fetch_mof_csv(url: str) -> pd.DataFrame:
    """MOF CSV URL을 내려받아 Date 인덱스 DataFrame으로 파싱한다."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text), skiprows=1)
    if "Date" not in df.columns:
        return pd.DataFrame()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date")
    return df


def collect_mof_category(
    items: dict[str, dict],
    category: str,
    start_date: str,
    end_date: str | None = None,
) -> pd.DataFrame:
    """카테고리 내 source='mof' 대상 일본 국채 금리를 주간 OHLC로 수집한다."""
    mof_items = {k: v for k, v in items.items() if v.get("source") == "mof"}
    if not mof_items:
        return pd.DataFrame()

    frames_raw = []
    for url in (MOF_HIST_URL, MOF_CURR_URL):
        try:
            frames_raw.append(_fetch_mof_csv(url))
        except Exception as exc:
            print(f"[WARN] MOF fetch failed ({url}): {exc}")

    if not frames_raw:
        return pd.DataFrame()

    raw = pd.concat(frames_raw)
    raw = raw[~raw.index.duplicated(keep="last")].sort_index()
    raw = raw.loc[raw.index >= pd.to_datetime(start_date)]
    if end_date:
        raw = raw.loc[raw.index <= pd.to_datetime(end_date)]

    out_frames = []
    for symbol, meta in mof_items.items():
        col = meta["tenor"]
        if col not in raw.columns:
            print(f"[WARN] MOF column '{col}' not found for {symbol}")
            continue
        series = pd.to_numeric(raw[col], errors="coerce").dropna()
        if series.empty:
            continue
        weekly = series.resample("W-FRI").ohlc().dropna()
        weekly = weekly.reset_index()
        weekly["Date"] = weekly["Date"].dt.strftime("%Y-%m-%d")
        weekly.columns = ["Date", "Open", "High", "Low", "Close"]
        weekly["Symbol"] = symbol
        weekly["Name"] = meta.get("name", symbol)
        weekly["Category"] = category
        out_frames.append(weekly)

    return pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()
