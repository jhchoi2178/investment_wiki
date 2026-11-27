"""
주간(Weekly) OHLC CSV 데이터를 읽어 Plotly.js 기반 인터랙티브 캔들 대시보드 HTML을 생성한다.
"""

import argparse
import json
from pathlib import Path
import pandas as pd

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Investment Wiki - Daily OHLC Dashboard</title>
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
    .controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
    select, label { font-size: 0.9rem; }
    select { background: #0f172a; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 6px 10px; }
    #chart { width: 100%; height: calc(100vh - 80px); min-height: 520px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Investment Wiki · Daily OHLC</h1>
      <nav>
        <a href="index.html" class="active">Daily OHLC</a>
        <a href="spread.html">Spread Analysis</a>
      </nav>
    </div>
    <div class="controls">
      <label>카테고리: <select id="catSelect"></select></label>
      <label>지표: <select id="symSelect"></select></label>
      <label><input type="checkbox" id="maCheck" checked /> 20일 이동평균</label>
    </div>
  </header>
  <div id="chart"></div>
  <script>
    const DATA = __DATA_JSON__;
    const catSelect = document.getElementById("catSelect");
    const symSelect = document.getElementById("symSelect");
    const maCheck = document.getElementById("maCheck");

    Object.keys(DATA).forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat; opt.textContent = cat.toUpperCase();
      catSelect.appendChild(opt);
    });

    function updateSymbols() {
      const cat = catSelect.value;
      symSelect.innerHTML = "";
      Object.entries(DATA[cat]).forEach(([sym, info]) => {
        const opt = document.createElement("option");
        opt.value = sym; opt.textContent = `${sym} (${info.name})`;
        symSelect.appendChild(opt);
      });
      renderChart();
    }

    function calcSMA(arr, n) {
      return arr.map((_, i) => i < n - 1 ? null : arr.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0) / n);
    }

    function renderChart() {
      const info = DATA[catSelect.value][symSelect.value];
      const traces = [{
        x: info.date, open: info.open, high: info.high, low: info.low, close: info.close,
        type: "candlestick", name: symSelect.value,
        increasing: { line: { color: "#22c55e" } }, decreasing: { line: { color: "#ef4444" } }
      }];
      if (maCheck.checked) {
        traces.push({
          x: info.date, y: calcSMA(info.close, 20),
          type: "scatter", mode: "lines", name: "20W SMA",
          line: { color: "#38bdf8", width: 1.5 }
        });
      }
      Plotly.newPlot("chart", traces, {
        template: "plotly_dark",
        paper_bgcolor: "#0f172a", plot_bgcolor: "#0f172a",
        title: `${symSelect.value} · ${info.name}`,
        xaxis: { rangeslider: { visible: false } },
        margin: { t: 48, r: 24, b: 40, l: 56 }
      }, { responsive: true });
    }

    catSelect.addEventListener("change", updateSymbols);
    symSelect.addEventListener("change", renderChart);
    maCheck.addEventListener("change", renderChart);
    updateSymbols();
  </script>
</body>
</html>
"""


def load_weekly_data(data_dir: Path) -> dict:
    """data_dir 내 모든 CSV 파일을 읽어 카테고리/심볼별 JSON 구조로 변환한다."""
    result: dict = {}
    for csv_path in sorted(data_dir.glob("*.csv")):
        cat = csv_path.stem
        df = pd.read_csv(csv_path)
        if df.empty:
            continue
        result[cat] = {}
        for sym, grp in df.groupby("Symbol"):
            grp = grp.sort_values("Date")
            result[cat][sym] = {
                "name": str(grp["Name"].iloc[0]) if "Name" in grp.columns else sym,
                "date": grp["Date"].tolist(),
                "open": grp["Open"].round(4).tolist(),
                "high": grp["High"].round(4).tolist(),
                "low": grp["Low"].round(4).tolist(),
                "close": grp["Close"].round(4).tolist(),
            }
    return result


def build_dashboard(data_dir: Path, output_path: Path) -> None:
    """대시보드 HTML 파일을 생성한다."""
    data = load_weekly_data(data_dir)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"[INFO] Dashboard generated: {output_path} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build weekly OHLC HTML dashboard")
    parser.add_argument("--data-dir", type=Path, default=Path("data/weekly"))
    parser.add_argument("--output", type=Path, default=Path("data/weekly/dashboard.html"))
    args = parser.parse_args()
    build_dashboard(args.data_dir, args.output)
