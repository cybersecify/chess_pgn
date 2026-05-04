"""
Generate an interactive HTML chart of rating progress day by day across all formats.

Creates data/{username}_progress.html and opens it in the browser.

Usage:
    .venv/bin/python queries/daily_progress.py
    .venv/bin/python queries/daily_progress.py --user neopaque
    .venv/bin/python queries/daily_progress.py --no-open   # save without opening
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("Error: duckdb not installed.", file=sys.stderr)
    sys.exit(1)

QUERY = """
WITH daily AS (
  SELECT
    time_class,
    strftime(to_timestamp(end_time), '%Y-%m-%d') AS day,
    CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS my_elo,
    CASE WHEN color = 'white' THEN black_elo ELSE white_elo END AS opp_elo,
    user_result,
    end_time,
    ROW_NUMBER() OVER (
      PARTITION BY time_class, strftime(to_timestamp(end_time), '%Y-%m-%d')
      ORDER BY end_time DESC
    ) AS rn
  FROM games
  WHERE (white = '{username}' OR black = '{username}')
    AND time_class IN ('bullet', 'blitz', 'rapid', 'daily')
    AND end_time IS NOT NULL AND color IS NOT NULL
    AND CASE WHEN color = 'white' THEN white_elo ELSE black_elo END IS NOT NULL
),
daily_stats AS (
  SELECT
    time_class, day,
    MAX(CASE WHEN rn = 1 THEN my_elo END) AS elo_eod,
    COUNT(*)                                                                       AS games,
    SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END)                        AS wins,
    SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END)                        AS losses,
    SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END)                        AS draws,
    ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
  FROM daily
  GROUP BY time_class, day
)
SELECT time_class, day, elo_eod, games, wins, losses, draws, win_pct
FROM daily_stats
ORDER BY time_class, day
"""

FORMAT_COLORS = {
    "rapid":  {"border": "#22c55e", "bg": "rgba(34,197,94,0.08)"},
    "blitz":  {"border": "#f97316", "bg": "rgba(249,115,22,0.08)"},
    "bullet": {"border": "#3b82f6", "bg": "rgba(59,130,246,0.08)"},
    "daily":  {"border": "#a855f7", "bg": "rgba(168,85,247,0.08)"},
}


def build_html(username: str, rows: list[tuple]) -> str:
    # Organise by format
    formats: dict[str, list[dict]] = {}
    for time_class, day, elo_eod, games, wins, losses, draws, win_pct in rows:
        if time_class not in formats:
            formats[time_class] = []
        formats[time_class].append({
            "x": day,
            "y": elo_eod,
            "games": games,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_pct": win_pct,
        })

    datasets = []
    for fmt, color in FORMAT_COLORS.items():
        if fmt not in formats:
            continue
        points = formats[fmt]
        datasets.append({
            "label": fmt.capitalize(),
            "data": [{"x": p["x"], "y": p["y"]} for p in points],
            "meta": points,
            "borderColor": color["border"],
            "backgroundColor": color["bg"],
            "borderWidth": 2,
            "pointRadius": 3,
            "pointHoverRadius": 6,
            "tension": 0.3,
            "fill": False,
        })

    # Build per-format summary for the stats cards
    summary: dict[str, dict] = {}
    for fmt, points in formats.items():
        elos = [p["y"] for p in points if p["y"] is not None]
        total_games = sum(p["games"] for p in points)
        total_wins  = sum(p["wins"]  for p in points)
        summary[fmt] = {
            "current": elos[-1] if elos else "—",
            "peak":    max(elos) if elos else "—",
            "low":     min(elos) if elos else "—",
            "games":   total_games,
            "win_pct": round(100.0 * total_wins / total_games, 1) if total_games else 0,
        }

    datasets_json = json.dumps(datasets, ensure_ascii=False)
    summary_json  = json.dumps(summary,  ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{username} — Chess Progress</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 24px; }}
  h1   {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }}
  .sub {{ color: #94a3b8; font-size: 0.875rem; margin-bottom: 24px; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }}
  .card {{
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 14px 20px; min-width: 180px; flex: 1;
  }}
  .card-title {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;
                 letter-spacing: 0.05em; margin-bottom: 6px; }}
  .card-row   {{ display: flex; gap: 20px; align-items: baseline; }}
  .card-big   {{ font-size: 1.6rem; font-weight: 700; }}
  .card-small {{ font-size: 0.78rem; color: #94a3b8; }}
  .dot        {{ display: inline-block; width: 10px; height: 10px;
                 border-radius: 50%; margin-right: 6px; }}
  .chart-wrap {{
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 20px; position: relative;
  }}
  .chart-wrap canvas {{ max-height: 480px; }}
  .legend-hint {{ text-align: center; color: #64748b; font-size: 0.75rem; margin-top: 10px; }}
</style>
</head>
<body>

<h1>Chess Progress — {username}</h1>
<p class="sub">Rating history by day across all formats. Click legend to toggle.</p>

<div class="cards" id="cards"></div>

<div class="chart-wrap">
  <canvas id="chart"></canvas>
  <p class="legend-hint">Click a format in the legend to show/hide it &nbsp;·&nbsp; Hover for daily details</p>
</div>

<script>
const DATASETS = {datasets_json};
const SUMMARY  = {summary_json};
const FORMAT_COLORS = {{
  rapid:  '#22c55e', blitz: '#f97316', bullet: '#3b82f6', daily: '#a855f7'
}};

// Build stat cards
const cards = document.getElementById('cards');
const order = ['rapid', 'blitz', 'bullet', 'daily'];
order.forEach(fmt => {{
  const s = SUMMARY[fmt];
  if (!s) return;
  const col = FORMAT_COLORS[fmt] || '#64748b';
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = `
    <div class="card-title">
      <span class="dot" style="background:${{col}}"></span>${{fmt.charAt(0).toUpperCase() + fmt.slice(1)}}
    </div>
    <div class="card-row">
      <span class="card-big" style="color:${{col}}">${{s.current}}</span>
      <span class="card-small">current</span>
    </div>
    <div class="card-small" style="margin-top:6px">
      Peak <b style="color:#e2e8f0">${{s.peak}}</b> &nbsp;·&nbsp;
      Low <b style="color:#e2e8f0">${{s.low}}</b>
    </div>
    <div class="card-small" style="margin-top:4px">
      ${{s.games}} games &nbsp;·&nbsp; ${{s.win_pct}}% win rate
    </div>`;
  cards.appendChild(card);
}});

// Attach meta lookup by dataset label for tooltip
const metaByLabel = {{}};
DATASETS.forEach(ds => {{ metaByLabel[ds.label] = ds.meta; }});

// Build chart
const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{ datasets: DATASETS }},
  options: {{
    responsive: true,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{
        position: 'top',
        labels: {{ color: '#cbd5e1', padding: 20, usePointStyle: true }}
      }},
      tooltip: {{
        backgroundColor: '#1e293b',
        borderColor: '#334155',
        borderWidth: 1,
        titleColor: '#f1f5f9',
        bodyColor: '#cbd5e1',
        padding: 12,
        callbacks: {{
          title: items => items[0].label,
          label: item => {{
            const ds    = item.dataset;
            const meta  = (metaByLabel[ds.label] || [])[item.dataIndex];
            if (!meta) return ` ${{ds.label}}: ${{item.parsed.y}}`;
            return [
              ` ${{ds.label}}: ${{item.parsed.y}}`,
              `   Games: ${{meta.games}}  (W${{meta.wins}} L${{meta.losses}} D${{meta.draws}})`,
              `   Win%: ${{meta.win_pct}}%`,
            ];
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        type: 'time',
        time: {{ unit: 'month', tooltipFormat: 'yyyy-MM-dd' }},
        grid:  {{ color: '#1e3a5f' }},
        ticks: {{ color: '#64748b', maxTicksLimit: 14 }}
      }},
      y: {{
        grid:  {{ color: '#1e3a5f' }},
        ticks: {{ color: '#64748b' }},
        title: {{ display: true, text: 'Rating', color: '#64748b' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate interactive rating progress chart")
    parser.add_argument("--user", default=os.environ.get("CHESS_USERNAME", ""),
                        help="Chess.com username (default: $CHESS_USERNAME)")
    parser.add_argument("--no-open", action="store_true",
                        help="Save the HTML file but don't open the browser")
    args = parser.parse_args()

    username = args.user
    if not username:
        parser.error("No username. Pass --user or set CHESS_USERNAME.")

    db_path = Path("data") / f"{username}.duckdb"
    if not db_path.exists():
        print(f"Error: database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = duckdb.connect(str(db_path), read_only=True)
    rows = conn.execute(QUERY.format(username=username)).fetchall()
    conn.close()

    if not rows:
        print("No data found.", file=sys.stderr)
        sys.exit(1)

    html = build_html(username, rows)

    out_path = Path("data") / f"{username}_progress.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Saved: {out_path}")

    if not args.no_open:
        webbrowser.open(out_path.resolve().as_uri())
        print("Opened in browser.")


if __name__ == "__main__":
    main()
