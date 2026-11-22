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


def load_config(config_path: Path) -> dict:
    """YAML 설정 파일을 로드한다."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_collection(start_date: str, end_date: str | None, out_dir: Path) -> None:
    """모든 카테고리의 데이터를 수집하여 out_dir에 CSV 파일로 저장한다."""
    load_dotenv()
    config = load_config(DEFAULT_CONFIG)
    out_dir.mkdir(parents=True, exist_ok=True)

    for category, items in config.items():
        print(f"[INFO] Collecting category: {category}")
        frames = [
            collect_yf_category(items, category, start_date, end_date),
            collect_fred_category(items, category, start_date, end_date),
            collect_ecos_category(items, category, start_date, end_date),
            collect_mof_category(items, category, start_date, end_date),
        ]
        valid = [df for df in frames if not df.empty]
        if not valid:
            print(f"[WARN] No data collected for {category}")
            continue

        merged = pd.concat(valid, ignore_index=True)
        merged = merged.sort_values(["Symbol", "Date"]).reset_index(drop=True)
        out_file = out_dir / f"{category}.csv"
        merged.to_csv(out_file, index=False, encoding="utf-8-sig")
        print(f"[OK] Saved {len(merged)} rows -> {out_file}")


def main() -> None:
    """CLI 인자를 파싱하여 수집 파이프라인을 실행한다."""
    parser = argparse.ArgumentParser(description="주간 투자 지표 수집기")
    parser.add_argument("--start", default="2020-01-01", help="수집 시작일 (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="수집 종료일 (YYYY-MM-DD)")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="CSV 저장 폴더")
    args = parser.parse_args()

    run_collection(args.start, args.end, Path(args.out))


if __name__ == "__main__":
    main()
