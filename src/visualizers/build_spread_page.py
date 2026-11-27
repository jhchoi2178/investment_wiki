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
  <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 12px 24px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }
    .brand { display: flex; align-items: center; gap: 16px; }
    h1 { margin: 0; font-size: 1.15rem; color: #f8fafc; }
    nav { display: flex; gap: 8px; }
    nav a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; padding: 6px 12px; border-radius: 6px; border: 1px solid transparent; }
    nav a:hover { color: #f8fafc; background: #334155; }
    nav a.active { color: #f8fafc; background: #0f172a; border-color: #475569; }
    .controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    select, label, button { font-size: 0.85rem; }
    select { background: #0f172a; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 6px 10px; }
    .range-btns { display: flex; gap: 4px; }
    .range-btns button { background: #0f172a; color: #94a3b8; border: 1px solid #475569; border-radius: 5px; padding: 4px 9px; cursor: pointer; }
    .range-btns button:hover, .range-btns button.active { background: #334155; color: #f8fafc; border-color: #64748b; }
    .chart-wrap { position: relative; width: 100%; height: calc(100vh - 68px); min-height: 520px; }
    #chart { width: 100%; height: 100%; }
    #tooltip { position: absolute; display: none; z-index: 20; background: rgba(15, 23, 42, 0.92); padding: 8px 10px; border-radius: 6px; border: 1px solid #475569; font-size: 0.8rem; pointer-events: none; font-variant-numeric: tabular-nums; line-height: 1.45; white-space: nowrap; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Investment Wiki · Spreads</h1>
      <nav>
        <a href="index.html">Daily OHLC</a>
        <a href="spread.html" class="active">Spread Analysis</a>
        <a href="regime.html">Regime Analysis</a>
      </nav>
    </div>
    <div class="controls">
      <label>지표: <select id="spreadSelect"></select></label>
      <div class="range-btns">
        <button data-days="30">1M</button>
        <button data-days="90">3M</button>
        <button data-days="180">6M</button>
        <button data-days="365">1Y</button>
        <button data-days="0" class="active">ALL</button>
      </div>
    </div>
  </header>
  <div class="chart-wrap">
    <div id="tooltip"></div>
    <div id="chart"></div>
  </div>
  <script>
    const DATA = __DATA_JSON__;
    const spreadSelect = document.getElementById("spreadSelect");
    const tooltip = document.getElementById("tooltip");
    const chartEl = document.getElementById("chart");
    let activeDays = 0;

    const chart = LightweightCharts.createChart(chartEl, {
      layout: { background: { color: "#0f172a" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1e293b" }, horzLines: { color: "#1e293b" } },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#334155" },
      timeScale: { borderColor: "#334155", timeVisible: true },
    });

    const areaSeries = chart.addAreaSeries({
      lineColor: "#38bdf8", topColor: "rgba(56, 189, 248, 0.28)", bottomColor: "rgba(56, 189, 248, 0.02)",
      lineWidth: 2, lastValueVisible: true, priceLineVisible: true,
    });
    areaSeries.createPriceLine({ price: 0, color: "#f87171", lineWidth: 1.5, lineStyle: 2, axisLabelVisible: true });

    new ResizeObserver(() => chart.applyOptions({ width: chartEl.clientWidth, height: chartEl.clientHeight })).observe(chartEl);

    Object.entries(DATA).forEach(([key, info]) => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = info.title;
      spreadSelect.appendChild(opt);
    });

    function applyRange() {
      if (activeDays === 0) { chart.timeScale().fitContent(); return; }
      const info = DATA[spreadSelect.value];
      if (!info || !info.date.length) return;
      const last = info.date[info.date.length - 1];
      const fromDate = new Date(last);
      fromDate.setDate(fromDate.getDate() - activeDays);
      chart.timeScale().setVisibleRange({ from: fromDate.toISOString().slice(0, 10), to: last });
    }

    function renderChart() {
      const info = DATA[spreadSelect.value];
      if (!info) return;
      const points = info.date.map((d, i) => ({ time: d, value: info.spread[i] }));
      areaSeries.setData(points);
      applyRange();
    }

    chart.subscribeCrosshairMove(param => {
      if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
        tooltip.style.display = "none";
        return;
      }
      const pt = param.seriesData.get(areaSeries);
      if (!pt) { tooltip.style.display = "none"; return; }
      tooltip.innerHTML = `<b>${pt.time}</b><br/>Spread: <b style="color:#38bdf8">${pt.value.toFixed(4)}</b>`;
      tooltip.style.display = "block";
      const left = Math.min(param.point.x + 14, chartEl.clientWidth - tooltip.offsetWidth - 12);
      const top = Math.min(param.point.y + 14, chartEl.clientHeight - tooltip.offsetHeight - 12);
      tooltip.style.left = Math.max(8, left) + "px";
      tooltip.style.top = Math.max(8, top) + "px";
    });

    document.querySelectorAll(".range-btns button").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".range-btns button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeDays = parseInt(btn.dataset.days, 10);
        applyRange();
      });
    });

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
        merged = pd.merge(a, b, on="Date", how="inner").sort_values("Date")
        if merged.empty:
            continue
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
