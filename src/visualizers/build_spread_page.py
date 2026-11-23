"""
장단기 금리차(10Y-2Y) 및 원유 현·선물 스프레드(선물-현물) 데이터를 계산해
독립된 Plotly.js 기반 인터랙티브 분석 페이지(spread.html)를 생성한다.
"""

import argparse
import json
from pathlib import Path
import pandas as pd

SPREAD_SPECS = [
    ("bonds", "US_10Y", "US_2Y", "US_10Y_2Y", "미국 장단기 금리차 (10Y - 2Y, %p)"),
    ("bonds", "KR_10Y", "KR_2Y", "KR_10Y_2Y", "한국 장단기 금리차 (10Y - 2Y, %p)"),
    ("bonds", "JP_10Y", "JP_2Y", "JP_10Y_2Y", "일본 장단기 금리차 (10Y - 2Y, %p)"),
    ("commodities", "WTI_FUT", "WTI_SPOT", "WTI_FUT_SPOT", "WTI유 현·선물 스프레드 (선물 - 현물, USD)"),
    ("commodities", "BRENT_FUT", "BRENT_SPOT", "BRENT_FUT_SPOT", "브렌트유 현·선물 스프레드 (선물 - 현물, USD)"),
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Investment Wiki - Spread Analysis</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 16px 24px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }
    .brand { display: flex; align-items: center; gap: 16px; }
    h1 { margin: 0; font-size: 1.2rem; color: #f8fafc; }
    nav { display: flex; gap: 8px; }
    nav a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; padding: 6px 12px; border-radius: 6px; border: 1px solid transparent; }
    nav a:hover { color: #f8fafc; background: #334155; }
    nav a.active { color: #f8fafc; background: #0f172a; border-color: #475569; }
    select { background: #0f172a; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 6px 10px; font-size: 0.9rem; }
    #chart { width: 100%; height: calc(100vh - 80px); min-height: 520px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Investment Wiki · Spreads</h1>
      <nav>
        <a href="index.html">Weekly OHLC</a>
        <a href="spread.html" class="active">Spread Analysis</a>
      </nav>
    </div>
    <div class="controls">
      <label>지표: <select id="spreadSelect"></select></label>
    </div>
  </header>
  <div id="chart"></div>
  <script>
    const DATA = __DATA_JSON__;
    const spreadSelect = document.getElementById("spreadSelect");

    Object.entries(DATA).forEach(([key, info]) => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = info.title;
      spreadSelect.appendChild(opt);
    });

    function renderChart() {
      const info = DATA[spreadSelect.value];
      if (!info) return;
      const trace = {
        x: info.date,
        y: info.spread,
        type: "scatter",
        mode: "lines",
        name: info.title,
        line: { color: "#38bdf8", width: 2 },
        fill: "tozeroy",
        fillcolor: "rgba(56, 189, 248, 0.15)"
      };
      const layout = {
        template: "plotly_dark",
        paper_bgcolor: "#0f172a",
        plot_bgcolor: "#0f172a",
        title: info.title,
        shapes: [{
          type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0,
          line: { color: "#f87171", width: 1.5, dash: "dash" }
        }],
        margin: { t: 48, r: 24, b: 40, l: 56 }
      };
      Plotly.newPlot("chart", [trace], layout, { responsive: true });
    }

    spreadSelect.addEventListener("change", renderChart);
    renderChart();
  </script>
</body>
</html>
"""


def compute_spreads(data_dir: Path) -> dict:
    """CSV 파일에서 대상 심볼을 추출해 날짜 기준 병합 후 스프레드를 계산한다."""
    dfs = {}
    for cat in ("bonds", "commodities"):
        path = data_dir / f"{cat}.csv"
        if path.exists():
            dfs[cat] = pd.read_csv(path)

    result: dict = {}
    for cat, sym_a, sym_b, key, title in SPREAD_SPECS:
        df = dfs.get(cat)
        if df is None or df.empty:
            continue
        a = df[df["Symbol"] == sym_a][["Date", "Close"]].rename(columns={"Close": "A"})
        b = df[df["Symbol"] == sym_b][["Date", "Close"]].rename(columns={"Close": "B"})
        if a.empty or b.empty:
            continue
        a["Week"] = pd.to_datetime(a["Date"]).dt.to_period("W-FRI")
        b["Week"] = pd.to_datetime(b["Date"]).dt.to_period("W-FRI")
        merged = pd.merge(a[["Week", "A"]], b[["Week", "B"]], on="Week", how="inner").sort_values("Week")
        if merged.empty:
            continue
        merged["Date"] = merged["Week"].dt.end_time.dt.strftime("%Y-%m-%d")
        merged["Spread"] = (merged["A"] - merged["B"]).round(4)
        result[key] = {
            "title": title,
            "date": merged["Date"].tolist(),
            "spread": merged["Spread"].tolist(),
        }
    return result


def build_spread_page(data_dir: Path, output_path: Path) -> None:
    """스프레드 분석 HTML 페이지를 생성한다."""
    data = compute_spreads(data_dir)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"[INFO] Spread page generated: {output_path} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build spread analysis HTML page")
    parser.add_argument("--data-dir", type=Path, default=Path("data/weekly"))
    parser.add_argument("--output", type=Path, default=Path("data/weekly/spread.html"))
    args = parser.parse_args()
    build_spread_page(args.data_dir, args.output)
