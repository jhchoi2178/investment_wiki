"""
전체 투자 지표 주간 OHLC 데이터 수집 실행 스크립트.
config/tickers.yaml을 읽어 yfinance, FRED, ECOS 수집기를 실행하고 카테고리별 CSV로 저장한다.
"""

import argparse
from pathlib import Path
import pandas as pd
import yaml
from dotenv import load_dotenv

from collectors.ecos_collector import collect_ecos_category
from collectors.fred_collector import collect_fred_category
from collectors.mof_collector import collect_mof_category
from collectors.yf_collector import collect_yf_category

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT_DIR / "config" / "tickers.yaml"
DEFAULT_OUT_DIR = ROOT_DIR / "data"


from datetime import datetime, timedelta


def load_config(config_path: Path) -> dict:
    """YAML 설정 파일을 로드한다."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _collect_item(symbol: str, meta: dict, category: str, start: str, end: str | None) -> pd.DataFrame:
    """단일 심볼에 대해 해당 source 수집기를 호출한다."""
    sub = {symbol: meta}
    src = meta.get("source")
    if src == "yfinance":
        return collect_yf_category(sub, category, start, end)
    if src == "fred":
        return collect_fred_category(sub, category, start, end)
    if src == "ecos":
        return collect_ecos_category(sub, category, start, end)
    if src == "mof":
        return collect_mof_category(sub, category, start, end)
    return pd.DataFrame()


def run_collection(start_date: str, end_date: str | None, out_dir: Path) -> None:
    """기존 CSV와 비교해 부족한 기간(과거/최신)만 증분 수집하여 저장한다."""
    load_dotenv()
    config = load_config(DEFAULT_CONFIG)
    out_dir.mkdir(parents=True, exist_ok=True)
    today_str = end_date or datetime.today().strftime("%Y-%m-%d")

    for category, items in config.items():
        print(f"[INFO] Collecting category: {category}")
        out_file = out_dir / f"{category}.csv"
        existing_df = pd.read_csv(out_file) if out_file.exists() else pd.DataFrame()
        frames = [existing_df] if not existing_df.empty else []

        for symbol, meta in items.items():
            sym_df = existing_df[existing_df["Symbol"] == symbol] if not existing_df.empty else pd.DataFrame()
            if sym_df.empty:
                df = _collect_item(symbol, meta, category, start_date, end_date)
                if not df.empty:
                    frames.append(df)
                continue

            min_d = sym_df["Date"].min()
            max_d = sym_df["Date"].max()
            if start_date < min_d:
                back_end = (pd.to_datetime(min_d) - timedelta(days=1)).strftime("%Y-%m-%d")
                df_back = _collect_item(symbol, meta, category, start_date, back_end)
                if not df_back.empty:
                    frames.append(df_back)
            if max_d < today_str:
                fwd_start = (pd.to_datetime(max_d) + timedelta(days=1)).strftime("%Y-%m-%d")
                df_fwd = _collect_item(symbol, meta, category, fwd_start, end_date)
                if not df_fwd.empty:
                    frames.append(df_fwd)

        valid = [df for df in frames if not df.empty]
        if not valid:
            print(f"[WARN] No data collected for {category}")
            continue

        merged = pd.concat(valid, ignore_index=True)
        merged = merged.drop_duplicates(subset=["Symbol", "Date"], keep="last")
        merged = merged.sort_values(["Symbol", "Date"]).reset_index(drop=True)
        merged.to_csv(out_file, index=False, encoding="utf-8-sig")
        print(f"[OK] Saved {len(merged)} rows -> {out_file}")


def main() -> None:
    """CLI 인자를 파싱하여 수집 파이프라인을 실행한다."""
    parser = argparse.ArgumentParser(description="일간 투자 지표 증분 수집기")
    parser.add_argument("--start", default="2000-01-01", help="수집 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="수집 종료일 (YYYY-MM-DD)")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="CSV 저장 폴더")
    args = parser.parse_args()

    run_collection(args.start, args.end, Path(args.out))


if __name__ == "__main__":
    main()
