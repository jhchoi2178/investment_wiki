"""
일간(Daily) OHLC CSV 데이터를 읽어 TradingView Lightweight Charts 기반 인터랙티브 캔들 대시보드 HTML을 생성한다.
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
    const catSelect = document.getElementById("catSelect");
    const symSelect = document.getElementById("symSelect");
    const maCheck = document.getElementById("maCheck");
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

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#22c55e", downColor: "#ef4444",
      borderUpColor: "#22c55e", borderDownColor: "#ef4444",
      wickUpColor: "#22c55e", wickDownColor: "#ef4444",
    });
    const maSeries = chart.addLineSeries({
      color: "#38bdf8", lineWidth: 1.5,
      lastValueVisible: true, priceLineVisible: true,
    });

    new ResizeObserver(() => chart.applyOptions({ width: chartEl.clientWidth, height: chartEl.clientHeight })).observe(chartEl);

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

    function applyRange() {
      if (activeDays === 0) { chart.timeScale().fitContent(); return; }
      const info = DATA[catSelect.value][symSelect.value];
      if (!info || !info.date.length) return;
      const last = info.date[info.date.length - 1];
      const fromDate = new Date(last);
      fromDate.setDate(fromDate.getDate() - activeDays);
      chart.timeScale().setVisibleRange({ from: fromDate.toISOString().slice(0, 10), to: last });
    }

    function renderChart() {
      const info = DATA[catSelect.value][symSelect.value];
      const candles = info.date.map((d, i) => ({
        time: d, open: info.open[i], high: info.high[i], low: info.low[i], close: info.close[i]
      }));
      candleSeries.setData(candles);

      const maData = [];
      for (let i = 19; i < candles.length; i++) {
        const sum = candles.slice(i - 19, i + 1).reduce((a, b) => a + b.close, 0);
        maData.push({ time: candles[i].time, value: +(sum / 20).toFixed(4) });
      }
      maSeries.setData(maCheck.checked ? maData : []);
      applyRange();
    }

    chart.subscribeCrosshairMove(param => {
      if (!param.point || !param.time || param.point.x < 0 || param.point.y < 0) {
        tooltip.style.display = "none";
        return;
      }
      const bar = param.seriesData.get(candleSeries);
      if (!bar) { tooltip.style.display = "none"; return; }
      const ma = param.seriesData.get(maSeries);
      const maTxt = ma != null ? `<br/><span style="color:#38bdf8">20D SMA: ${ma.value.toFixed(4)}</span>` : "";
      tooltip.innerHTML = `<b>${bar.time}</b><br/>O: ${bar.open} &nbsp; H: ${bar.high}<br/>L: ${bar.low} &nbsp; C: <b>${bar.close}</b>${maTxt}`;
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
