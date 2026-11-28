"""
매크로 국면(VIX 공포/안정, 장단기 금리차 역전/정상)별 자산 수익률 및 MDD를 비교하는
인터랙티브 분석 페이지(regime.html)를 생성한다.
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
  <title>Investment Wiki - Regime Analysis</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    header { padding: 12px 24px; background: #1e293b; border-bottom: 1px solid #334155; display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }
    .brand { display: flex; align-items: center; gap: 16px; }
    h1 { margin: 0; font-size: 1.15rem; color: #f8fafc; }
    nav { display: flex; gap: 8px; }
    nav a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; padding: 6px 12px; border-radius: 6px; border: 1px solid transparent; }
    nav a:hover { color: #f8fafc; background: #334155; }
    nav a.active { color: #f8fafc; background: #0f172a; border-color: #475569; }
    select { background: #0f172a; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 6px 10px; font-size: 0.85rem; }
    main { padding: 20px 24px; max-width: 1200px; margin: 0 auto; }
    .summary { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
    .card { background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 12px 16px; min-width: 200px; }
    .card .label { font-size: 0.8rem; color: #94a3b8; }
    .card .val { font-size: 1.1rem; font-weight: 600; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; font-size: 0.88rem; }
    th, td { padding: 10px 12px; text-align: right; border-bottom: 1px solid #334155; }
    th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align: left; }
    th { background: #0f172a; color: #94a3b8; font-weight: 600; }
    tr:hover { background: #263348; }
    .pos { color: #22c55e; }
    .neg { color: #ef4444; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Investment Wiki · Regimes</h1>
      <nav>
        <a href="index.html">Daily OHLC</a>
        <a href="spread.html">Spread Analysis</a>
        <a href="regime.html" class="active">Regime Analysis</a>
      </nav>
    </div>
    <div class="controls">
      <label>국면 기준: <select id="regimeSelect"></select></label>
      <label>카테고리: <select id="catSelect"></select></label>
    </div>
  </header>
  <main>
    <div class="summary" id="summary"></div>
    <table>
      <thead id="thead"></thead>
      <tbody id="tbody"></tbody>
    </table>
  </main>
  <script>
    const DATA = __DATA_JSON__;
    const regimeSelect = document.getElementById("regimeSelect");
    const catSelect = document.getElementById("catSelect");
    const summaryEl = document.getElementById("summary");
    const thead = document.getElementById("thead");
    const tbody = document.getElementById("tbody");

    Object.entries(DATA).forEach(([k, v]) => {
      const opt = document.createElement("option");
      opt.value = k; opt.textContent = v.title;
      regimeSelect.appendChild(opt);
    });

    function updateCategories() {
      const reg = DATA[regimeSelect.value];
      catSelect.innerHTML = "";
      Object.keys(reg.categories).forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat; opt.textContent = cat.toUpperCase();
        catSelect.appendChild(opt);
      });
      renderTable();
    }

    function fmtPct(v) {
      if (v == null) return "-";
      const cls = v >= 0 ? "pos" : "neg";
      return `<span class="${cls}">${v >= 0 ? "+" : ""}${v.toFixed(1)}%</span>`;
    }

    function renderTable() {
      const reg = DATA[regimeSelect.value];
      const rows = reg.categories[catSelect.value] || [];
      summaryEl.innerHTML = reg.regimes.map(g =>
        `<div class="card"><div class="label">${g.label}</div><div class="val">${g.days}일</div></div>`
      ).join("");
      thead.innerHTML = `<tr><th>심볼</th><th>자산명</th>${reg.regimes.map(g =>
        `<th>${g.label}<br/>연수익률</th><th>${g.label}<br/>MDD</th>`
      ).join("")}</tr>`;
      tbody.innerHTML = rows.map(r => `
        <tr>
          <td><b>${r.symbol}</b></td><td>${r.name}</td>
          ${r.stats.map(s => `<td>${fmtPct(s.ret)}</td><td class="neg">${s.mdd != null ? s.mdd.toFixed(1) + "%" : "-"}</td>`).join("")}
        </tr>
      `).join("");
    }

    regimeSelect.addEventListener("change", updateCategories);
    catSelect.addEventListener("change", renderTable);
    updateCategories();
  </script>
</body>
</html>
"""


def _calc_stats(returns: pd.Series) -> dict:
    """일간 수익률 시리즈에서 연환산 수익률(%)과 MDD(%)를 계산한다."""
    if len(returns) < 5:
        return {"ret": None, "mdd": None}
    ann_ret = float(returns.mean() * 252 * 100)
    cum = (1 + returns).cumprod()
    mdd = float(((cum / cum.cummax()) - 1).min() * 100)
    return {"ret": round(ann_ret, 2), "mdd": round(mdd, 2)}


def compute_regimes(data_dir: Path) -> dict:
    """VIX(4구간: 10/20/30) 및 미 장단기 금리차 국면별 자산 성과를 계산한다."""
    dfs = {p.stem: pd.read_csv(p) for p in sorted(data_dir.glob("*.csv"))}
    idx_df = dfs.get("indices", pd.DataFrame())
    bond_df = dfs.get("bonds", pd.DataFrame())

    regime_defs = {}
    if not idx_df.empty:
        vix = idx_df[idx_df["Symbol"] == "VIX"][["Date", "Close"]].set_index("Date")["Close"]
        if not vix.empty:
            regime_defs["vix"] = (
                "VIX 4구간 국면 (기준: 10 / 20 / 30)",
                [
                    ("초안정 (< 10)", vix < 10),
                    ("안정 (10~20)", (vix >= 10) & (vix < 20)),
                    ("경계 (20~30)", (vix >= 20) & (vix < 30)),
                    ("공포 (≥ 30)", vix >= 30),
                ],
            )
    if not bond_df.empty:
        us10 = bond_df[bond_df["Symbol"] == "US_10Y"][["Date", "Close"]].set_index("Date")["Close"]
        us2 = bond_df[bond_df["Symbol"] == "US_2Y"][["Date", "Close"]].set_index("Date")["Close"]
        spread = (us10 - us2).dropna()
        if not spread.empty:
            regime_defs["yc"] = (
                "미국 장단기 금리차 국면 (10Y-2Y)",
                [("정상 (≥ 0)", spread >= 0), ("역전 (< 0)", spread < 0)],
            )

    result = {}
    for key, (title, groups) in regime_defs.items():
        cats = {}
        for cat in ("indices", "commodities", "fx", "stocks"):
            df = dfs.get(cat)
            if df is None or df.empty:
                continue
            rows = []
            for sym, grp in df.groupby("Symbol"):
                grp = grp.sort_values("Date").set_index("Date")
                ret = grp["Close"].pct_change().dropna()
                stats = []
                for _, mask in groups:
                    aligned = ret.index.intersection(mask.index)
                    stats.append(_calc_stats(ret.loc[aligned][mask.loc[aligned]]) if not aligned.empty else {"ret": None, "mdd": None})
                rows.append({
                    "symbol": sym,
                    "name": str(grp["Name"].iloc[0]) if "Name" in grp.columns else sym,
                    "stats": stats,
                })
            if rows:
                cats[cat] = rows
        result[key] = {
            "title": title,
            "regimes": [{"label": lbl, "days": int(mask.sum())} for lbl, mask in groups],
            "categories": cats,
        }
    return result


def build_regime_page(data_dir: Path, output_path: Path) -> None:
    """국면 분석 HTML 페이지를 생성한다."""
    data = compute_regimes(data_dir)
    html = HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"[INFO] Regime page generated: {output_path} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build regime analysis HTML page")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("_site/regime.html"))
    args = parser.parse_args()
    build_regime_page(args.data_dir, args.output)
