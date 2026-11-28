"""
매크로·자산군 상관관계 4가지 분석(정적 히트맵, 롤링 상관, 시차 Lag, 클러스터링)을
서브 탭으로 제공하는 correlation.html을 생성한다.
"""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Investment Wiki - Correlation Analysis</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 12px 24px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }
    .brand { display: flex; align-items: center; gap: 16px; }
    h1 { margin: 0; font-size: 1.15rem; color: #f8fafc; }
    nav, .subtabs { display: flex; gap: 8px; flex-wrap: wrap; }
    nav a, .subtabs button { color: #94a3b8; text-decoration: none; font-size: 0.88rem; padding: 6px 12px; border-radius: 6px; border: 1px solid transparent; background: transparent; cursor: pointer; }
    nav a:hover, .subtabs button:hover { color: #f8fafc; background: #334155; }
    nav a.active, .subtabs button.active { color: #f8fafc; background: #0f172a; border-color: #475569; }
    .toolbar { padding: 12px 24px; background: #162032; border-bottom: 1px solid #334155; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }
    .controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; font-size: 0.85rem; }
    select { background: #0f172a; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 5px 10px; font-size: 0.85rem; }
    #chart { width: 100%; height: calc(100vh - 130px); min-height: 540px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Investment Wiki · Correlation</h1>
      <nav>
        <a href="index.html">Daily OHLC</a>
        <a href="spread.html">Spread Analysis</a>
        <a href="regime.html">Regime Analysis</a>
        <a href="correlation.html" class="active">Correlation</a>
      </nav>
    </div>
  </header>
  <div class="toolbar">
    <div class="subtabs">
      <button class="active" data-tab="heatmap">1. 정적 히트맵</button>
      <button data-tab="rolling">2. 롤링 상관관계</button>
      <button data-tab="lag">3. 시차(Lag) 분석</button>
      <button data-tab="cluster">4. 클러스터링</button>
    </div>
    <div class="controls" id="controls"></div>
  </div>
  <div id="chart"></div>
  <script>
    const DATA = __DATA_JSON__;
    let activeTab = "heatmap";
    const controlsEl = document.getElementById("controls");

    function corr(x, y) {
      const n = x.length;
      if (n < 5) return null;
      const mx = x.reduce((a, b) => a + b, 0) / n;
      const my = y.reduce((a, b) => a + b, 0) / n;
      let num = 0, dx = 0, dy = 0;
      for (let i = 0; i < n; i++) {
        const a = x[i] - mx, b = y[i] - my;
        num += a * b; dx += a * a; dy += b * b;
      }
      return (dx && dy) ? num / Math.sqrt(dx * dy) : null;
    }

    function alignPair(symA, symB) {
      const a = DATA.series[symA], b = DATA.series[symB];
      const mapB = new Map(b.date.map((d, i) => [d, b.ret[i]]));
      const dates = [], xa = [], yb = [];
      a.date.forEach((d, i) => {
        if (mapB.has(d)) { dates.push(d); xa.push(a.ret[i]); yb.push(mapB.get(d)); }
      });
      return { dates, xa, yb };
    }

    function renderControls() {
      const syms = DATA.symbols;
      const opts = syms.map(s => `<option value="${s}">${s}</option>`).join("");
      if (activeTab === "heatmap") {
        controlsEl.innerHTML = `<label>방식: <select id="methodSel"><option value="pearson">Pearson</option><option value="spearman">Spearman</option></select></label>`;
        document.getElementById("methodSel").onchange = renderChart;
      } else if (activeTab === "rolling") {
        controlsEl.innerHTML = `<label>자산 A: <select id="symA">${opts}</select></label><label>자산 B: <select id="symB">${opts}</select></label><label>기간: <select id="winSel"><option value="60">60일</option><option value="120">120일</option></select></label>`;
        document.getElementById("symA").value = syms.includes("US_10Y") ? "US_10Y" : syms[0];
        document.getElementById("symB").value = syms.includes("NASDAQ100") ? "NASDAQ100" : syms[1];
        ["symA", "symB", "winSel"].forEach(id => document.getElementById(id).onchange = renderChart);
      } else if (activeTab === "lag") {
        controlsEl.innerHTML = `<label>선행 자산 A: <select id="symA">${opts}</select></label><label>후행 자산 B: <select id="symB">${opts}</select></label>`;
        document.getElementById("symA").value = syms.includes("DXY") ? "DXY" : syms[0];
        document.getElementById("symB").value = syms.includes("KOSPI") ? "KOSPI" : syms[1];
        ["symA", "symB"].forEach(id => document.getElementById(id).onchange = renderChart);
      } else {
        controlsEl.innerHTML = `<span style="color:#94a3b8">상관거리(1-r) 기준 유사 자산 군집 정렬</span>`;
      }
      renderChart();
    }

    function renderChart() {
      const layoutBase = { template: "plotly_dark", paper_bgcolor: "#0f172a", plot_bgcolor: "#0f172a", margin: { t: 48, r: 24, b: 80, l: 90 } };
      if (activeTab === "heatmap" || activeTab === "cluster") {
        const key = activeTab === "cluster" ? "cluster" : document.getElementById("methodSel").value;
        const m = DATA.matrices[key];
        Plotly.newPlot("chart", [{
          z: m.z, x: m.labels, y: m.labels, type: "heatmap", colorscale: "RdBu", zmin: -1, zmax: 1, reversescale: true
        }], { ...layoutBase, title: activeTab === "cluster" ? "상관거리 기반 클러스터링 히트맵" : `정적 상관계수 히트맵 (${key.toUpperCase()})` }, { responsive: true });
      } else if (activeTab === "rolling") {
        const symA = document.getElementById("symA").value, symB = document.getElementById("symB").value;
        const win = parseInt(document.getElementById("winSel").value, 10);
        const { dates, xa, yb } = alignPair(symA, symB);
        const rx = [], ry = [];
        for (let i = win; i <= dates.length; i++) {
          rx.push(dates[i - 1]);
          ry.push(corr(xa.slice(i - win, i), yb.slice(i - win, i)));
        }
        Plotly.newPlot("chart", [{ x: rx, y: ry, type: "scatter", mode: "lines", line: { color: "#38bdf8", width: 2 } }],
          { ...layoutBase, title: `${symA} vs ${symB} (${win}일 롤링 상관계수)`, yaxis: { range: [-1, 1] }, shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: { color: "#f87171", dash: "dash" } }] }, { responsive: true });
      } else if (activeTab === "lag") {
        const symA = document.getElementById("symA").value, symB = document.getElementById("symB").value;
        const { xa, yb } = alignPair(symA, symB);
        const lags = [], vals = [];
        for (let k = -20; k <= 20; k++) {
          lags.push(k);
          const xSlice = k >= 0 ? xa.slice(0, xa.length - k) : xa.slice(-k);
          const ySlice = k >= 0 ? yb.slice(k) : yb.slice(0, yb.length + k);
          vals.push(corr(xSlice, ySlice));
        }
        Plotly.newPlot("chart", [{ x: lags, y: vals, type: "bar", marker: { color: vals.map(v => v >= 0 ? "#22c55e" : "#ef4444") } }],
          { ...layoutBase, title: `시차(Lag) 교차상관: ${symA}(t) vs ${symB}(t + Lag일)`, xaxis: { title: "Lag (일, 양수면 A가 선행)" }, yaxis: { range: [-0.5, 0.5] } }, { responsive: true });
      }
    }

    document.querySelectorAll(".subtabs button").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".subtabs button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeTab = btn.dataset.tab;
        renderControls();
      });
    });
    renderControls();
  </script>
</body>
</html>
"""


def _seriate_corr(corr_df: pd.DataFrame) -> list[str]:
    """상관거리(1-r) 기반 탐욕적 최근접 이웃 순서로 심볼을 군집 정렬한다."""
    remaining = list(corr_df.columns)
    order = [remaining.pop(0)]
    while remaining:
        last = order[-1]
        nxt = max(remaining, key=lambda s: corr_df.loc[last, s])
        order.append(nxt)
        remaining.remove(nxt)
    return order


def compute_correlation_data(data_dir: Path) -> dict:
    """카테고리별 일간 수익률(금리는 변화폭)을 병합해 상관계수 행렬과 시계열을 생성한다."""
    series_map = {}
    for cat in ("bonds", "fx", "commodities", "indices", "stocks"):
        path = data_dir / f"{cat}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        for sym, grp in df.groupby("Symbol"):
            grp = grp.sort_values("Date").drop_duplicates("Date").set_index("Date")
            s = grp["Close"].diff() if cat == "bonds" else grp["Close"].pct_change()
            s = s.dropna()
            if len(s) >= 60:
                series_map[sym] = s

    ret_df = pd.DataFrame(series_map).sort_index()
    pearson = ret_df.corr(method="pearson").round(3).fillna(0)
    spearman = ret_df.corr(method="spearman").round(3).fillna(0)
    cluster_order = _seriate_corr(pearson)
    clustered = pearson.loc[cluster_order, cluster_order]

    return {
        "symbols": list(ret_df.columns),
        "matrices": {
            "pearson": {"labels": list(pearson.columns), "z": pearson.values.tolist()},
            "spearman": {"labels": list(spearman.columns), "z": spearman.values.tolist()},
            "cluster": {"labels": cluster_order, "z": clustered.values.tolist()},
        },
        "series": {
            sym: {"date": s.index.tolist(), "ret": s.round(6).tolist()}
            for sym, s in series_map.items()
        },
    }


def build_correlation_page(data_dir: Path, output_path: Path) -> None:
    """상관관계 분석 HTML 페이지를 생성한다."""
    data = compute_correlation_data(data_dir)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"[INFO] Correlation page generated: {output_path} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build correlation analysis HTML page")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("_site/correlation.html"))
    args = parser.parse_args()
    build_correlation_page(args.data_dir, args.output)
